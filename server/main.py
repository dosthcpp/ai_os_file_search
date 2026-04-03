import asyncio
import hashlib as _hashlib
import json as _json
import re as _re
import sys
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from time import time as now
from typing import List
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from qdrant_client.models import Distance, VectorParams
from starlette.middleware.cors import CORSMiddleware

# Windows 콘솔 UTF-8 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 🔥 전역 변수로 선언만 (lazy loading)
client = None
embed_model = None

def get_client():
    global client
    if client is None:
        client = QdrantClient(url="https://qdrant.drakedognas.synology.me", port=443, https=True)
    return client

def get_embed_model():
    global embed_model
    if embed_model is None:
        from sentence_transformers import SentenceTransformer
        print("[LOAD] Loading embedding model...")
        embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[OK] Embedding model loaded")
    return embed_model

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                dead_connections.append(connection)
            except Exception as e:
                print("WS send error:", e)
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)

manager = ConnectionManager()

async def notify_file_change(action: str, path: str, node: dict | None = None):
    await manager.broadcast({"type": "file-changed", "action": action, "path": path, "node": node})

def build_tree(file_changes: list[dict]):
    root = {}
    for meta in file_changes:
        path = meta["path"]
        status = meta["status"]
        parts = path.replace("\\", "/").split("/")
        cur = root
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = {"_file": True, "status": status, "path": path}

    def to_node(name, obj):
        if "_file" in obj:
            return {"name": name, "type": "file", "status": obj["status"], "path": obj["path"]}
        return {"name": name, "type": "dir", "children": [to_node(k, v) for k, v in obj.items()]}
    return {"name": "root", "type": "dir", "children": [to_node(k, v) for k, v in root.items()]}

def build_tree_from_qdrant():
    client = get_client()
    records = client.scroll(collection_name="file_changes", with_payload=True, limit=10_000)[0]
    changes = [r.payload for r in records]
    return build_tree(changes)

async def notify_tree_update():
    tree = build_tree_from_qdrant()
    await manager.broadcast({"type": "tree", "tree": tree})

class FileStatus(str, Enum):
    added = "added"
    modified = "modified"
    deleted = "deleted"

class FileChangePayload(BaseModel):
    path: str
    status: FileStatus
    timestamp: float
    node: dict | None = None

class FileData(BaseModel):
    path: str
    summary: str
    embedding: list
    hash: str

class FileVersionData(BaseModel):
    path: str
    version: int
    diff: list[str]
    vector: list[float]
    summary: str
    hash: str
    change_type: str

class ChunkData(BaseModel):
    id: str
    vector: list[float]
    payload: dict

class DiffPayload(BaseModel):
    path: str
    old_text: str
    new_text: str

async def init_collections():
    print("[INFO] Initializing Qdrant collections...")
    client = get_client()
    collections = client.get_collections().collections
    names = {c.name for c in collections}
    for name in ["files", "file_changes", "file_diffs", "file_versions"]:
        if name not in names:
            size = 1 if name == "file_changes" else 384
            client.create_collection(collection_name=name, vectors_config=VectorParams(size=size, distance=Distance.COSINE))
    print("[OK] Qdrant collections ready")

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(init_collections())
    asyncio.create_task(asyncio.sleep(0.1)) # Warmup placeholder
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health():
    return {"status": "ok", "embed_model_loaded": embed_model is not None}

# (Essential API OS endpoints for File Indexing, Search, Diffing go here...)

@app.post("/api/file-change")
async def record_file_change(payload: FileChangePayload):
    client = get_client()
    client.upsert(collection_name="file_changes", points=[PointStruct(id=str(uuid4()), vector=[0.0], payload={"path": payload.path, "status": payload.status, "timestamp": payload.timestamp})])
    await notify_file_change(payload.status, payload.path, payload.node)
    await notify_tree_update()
    return {"ok": True}

# ── PoC v2-1: Security Audit (Core Feature) ────────────────────────────────

_DANGEROUS_PERMISSIONS = {
    "READ_SMS":                   {"score": 35, "reason": "Can silently read private SMS messages (OTP theft risk)"},
    "RECEIVE_SMS":                {"score": 25, "reason": "Can intercept incoming SMS in real time"},
    "INSTALL_PACKAGES":           {"score": 40, "reason": "Can silently install additional malicious APKs"},
    "READ_CONTACTS":              {"score": 20, "reason": "Can exfiltrate user contact list"},
    "RECORD_AUDIO":               {"score": 30, "reason": "Can activate microphone without user awareness"},
    "ACCESS_FINE_LOCATION":       {"score": 15, "reason": "Precise GPS tracking, possible stalkerware vector"},
    # ── Extended dangerous permissions ──────────────────────────────────────
    "CAMERA":                     {"score": 30, "reason": "Can silently capture photos/video without user knowledge"},
    "PROCESS_OUTGOING_CALLS":     {"score": 25, "reason": "Can intercept and redirect outgoing phone calls"},
    "READ_CALL_LOG":              {"score": 20, "reason": "Access to full call history — serious privacy violation"},
    "WRITE_SETTINGS":             {"score": 20, "reason": "Can modify system settings to establish persistence"},
    "BIND_ACCESSIBILITY_SERVICE": {"score": 45, "reason": "Highest risk — enables keylogging, overlay attacks, and UI automation abuse"},
    "GET_ACCOUNTS":               {"score": 15, "reason": "Can harvest Google/social account identifiers for credential stuffing"},
    "READ_PHONE_STATE":           {"score": 15, "reason": "Exposes IMEI and device fingerprint for persistent cross-app tracking"},
    "CALL_PHONE":              {"score": 20, "reason": "Can silently initiate phone calls — used in voice phishing (vishing) attacks"},
    "DISABLE_KEYGUARD":        {"score": 30, "reason": "Can bypass screen lock — used by ransomware to prevent victim from accessing device"},
    "WRITE_EXTERNAL_STORAGE":  {"score": 15, "reason": "Can write files to external storage — used for ransomware data staging and payload delivery"},
    "MANAGE_EXTERNAL_STORAGE": {"score": 35, "reason": "Full access to all files on external storage — high risk of ransomware or data theft"},
    "READ_MEDIA_IMAGES":       {"score": 15, "reason": "Access to private photos — privacy leak risk"},
    "READ_MEDIA_VIDEO":        {"score": 15, "reason": "Access to private videos — privacy leak risk"},
    "READ_MEDIA_AUDIO":        {"score": 15, "reason": "Access to private audio files — privacy leak risk"},
    "ACCESS_BACKGROUND_LOCATION": {"score": 25, "reason": "Continuous location tracking even when app is closed — stalkerware behavior"},
    "BODY_SENSORS":            {"score": 15, "reason": "Access to health/fitness data — sensitive PII leak"},
}

_SUSPICIOUS_URL_PATTERNS = [
    (_re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}"),
     "Direct IP address — no domain name, common evasion tactic", 20),
    (_re.compile(r'https?://[^\s"\']*(?:\.ru|\.biz|\.xyz|\.top)[^\s"\']*'),
     "High-risk TLD frequently associated with phishing campaigns", 20),
    (_re.compile(r'https?://[^\s"\']*(?:exfil|track|collect|evil|phish)[^\s"\']*'),
     "Keyword matching known data-exfiltration or phishing patterns", 20),
    # ── Extended URL patterns ────────────────────────────────────────────────
    (_re.compile(r'https?://[^\s"\']*:(?:4444|1337|31337|8888|6666|9999)/'),
     "Non-standard port associated with known C2/RAT frameworks (Metasploit/Cobalt Strike)", 25),
    (_re.compile(r'https?://[^\s"\']*(?:\.tk|\.pw|\.cf|\.ga|\.ml|\.gq|\.cc)[^\s"\']*'),
     "Free/disposable TLD commonly abused for phishing and malware distribution", 20),
    (_re.compile(r'https?://[^\s"\']*(?:dump|steal|upload|beacon|shell|backdoor|rat\b|c2\b|cnc|payload)[^\s"\']*', _re.IGNORECASE),
     "URL contains C2/RAT operational keywords indicating command-and-control infrastructure", 30),
    (_re.compile(r'https?://[^\s"\']*(?:%[0-9a-fA-F]{2}){4,}[^\s"\']*'),
     "Heavily percent-encoded URL — likely obfuscating malicious destination to bypass static analysis", 20),
    (_re.compile(r'https?://[a-z0-9]{12,30}\.[a-z]{2,6}/'),
     "Algorithmically-generated domain (DGA) pattern — characteristic of botnet C2 communication", 25),
    (_re.compile(r'https?://[^\s"\']*ngrok\.io[^\s"\']*'),
     "ngrok reverse-proxy tunnel — commonly used to expose local C2 servers from behind NAT", 25),
    (_re.compile(r'https?://[^\s"\']*(?:pastebin|ghostbin|hastebin|pastie|justpaste\.it)[^\s"\']*'),
     "Paste site URL — often used to host malicious scripts, configurations, or exfiltrated data", 20),
    (_re.compile(r'https?://[^\s"\']*(?:githubusercontent|bitbucket\.org|gitlab\.com)[^\s"\']*'),
     "Code hosting site — may be used to fetch secondary payloads or configuration from legitimate services", 15),
    (_re.compile(r'https?://[^\s"\']*(?:bit\.ly|t\.co|tinyurl\.com|is\.gd|buff\.ly|rebrand\.ly)[^\s"\']*'),
     "URL shortener — masks the final malicious destination to bypass security filters", 15),
]

_SENSITIVE_PI_PATTERNS = {
    "RRN":        r"\d{6}-\d{7}",
    "Bank":       r"\d{10,14}",
    "Email":      r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "CreditCard": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
    "Passport":   r"\b[A-Z]{1,2}[0-9]{7,9}\b",
}

# ── Security Audit Test Cases (10 pre-built scenarios) ───────────────────────
SECURITY_TEST_CASES = [
    {
        "id": "tc_01",
        "name": "TC-01: SMS OTP Stealer",
        "description": "Fake banking app harvesting one-time passwords by reading and intercepting incoming SMS messages",
        "manifest": '<manifest package="com.fake.banking.app">\n  <uses-permission android:name="android.permission.READ_SMS"/>\n  <uses-permission android:name="android.permission.RECEIVE_SMS"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="api_host">http://91.108.4.200/collect</string>\n  <string name="exfil_tag">sms_stealer_v3</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_02",
        "name": "TC-02: Silent Surveillance (Stalkerware)",
        "description": "Stalkerware silently activating camera, microphone, and GPS for comprehensive device surveillance",
        "manifest": '<manifest package="com.hidden.monitor">\n  <uses-permission android:name="android.permission.CAMERA"/>\n  <uses-permission android:name="android.permission.RECORD_AUDIO"/>\n  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="server">https://track.spy-hub.xyz/upload</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_03",
        "name": "TC-03: Banking Trojan (Overlay Attack)",
        "description": "Abuses AccessibilityService to intercept banking credentials via invisible overlay attacks",
        "manifest": '<manifest package="com.fake.flashlight">\n  <uses-permission android:name="android.permission.BIND_ACCESSIBILITY_SERVICE"/>\n  <uses-permission android:name="android.permission.READ_SMS"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="c2">http://banking-update.top/beacon</string>\n  <string name="payload">http://92.63.197.48/shell</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_04",
        "name": "TC-04: Spyware Package Dropper",
        "description": "Self-replicating spyware that silently installs additional malicious APKs and exfiltrates contacts",
        "manifest": '<manifest package="com.system.update.service">\n  <uses-permission android:name="android.permission.INSTALL_PACKAGES"/>\n  <uses-permission android:name="android.permission.READ_CONTACTS"/>\n  <uses-permission android:name="android.permission.RECEIVE_SMS"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="drop_url">https://payload-cdn.biz/rat_v2.apk</string>\n  <string name="exfil">http://data.evil-dump.xyz/upload</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_05",
        "name": "TC-05: Call Monitor & Interceptor",
        "description": "Intercepts outgoing calls, records audio, and harvests full call logs for surveillance or fraud",
        "manifest": '<manifest package="com.phone.optimizer">\n  <uses-permission android:name="android.permission.PROCESS_OUTGOING_CALLS"/>\n  <uses-permission android:name="android.permission.READ_CALL_LOG"/>\n  <uses-permission android:name="android.permission.RECORD_AUDIO"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="tracker">https://calltrack.ru/collect</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_06",
        "name": "TC-06: Account Credential Harvester",
        "description": "Harvests device account identifiers and IMEI fingerprint for large-scale credential stuffing",
        "manifest": '<manifest package="com.widget.launcher">\n  <uses-permission android:name="android.permission.GET_ACCOUNTS"/>\n  <uses-permission android:name="android.permission.READ_PHONE_STATE"/>\n  <uses-permission android:name="android.permission.WRITE_SETTINGS"/>\n</manifest>',
        "strings": '<resources>\n  <string name="api">https://xkqzwmplvnbrtdsa.cc/payload</string>\n  <string name="beacon">http://185.220.101.47/cnc</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_07",
        "name": "TC-07: Full APT Threat Package",
        "description": "Advanced persistent threat combining maximum-risk permissions with multiple covert C2 channels",
        "manifest": '<manifest package="com.android.system.update">\n  <uses-permission android:name="android.permission.BIND_ACCESSIBILITY_SERVICE"/>\n  <uses-permission android:name="android.permission.INSTALL_PACKAGES"/>\n  <uses-permission android:name="android.permission.READ_SMS"/>\n  <uses-permission android:name="android.permission.RECORD_AUDIO"/>\n  <uses-permission android:name="android.permission.CAMERA"/>\n  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>\n</manifest>',
        "strings": '<resources>\n  <string name="c2_primary">http://45.141.86.200:4444/backdoor</string>\n  <string name="c2_backup">https://update-service.top/shell</string>\n  <string name="exfil">http://data.phish-collect.ru/dump</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_08",
        "name": "TC-08: Obfuscated Phishing URLs",
        "description": "Uses heavily encoded and DGA-like domains to bypass static analysis and hide malicious destinations",
        "manifest": '<manifest package="com.media.player.pro">\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="endpoint">https://login-secure.tk/auth%2F%73%74%65%61%6C%2Fcreds</string>\n  <string name="cdn">http://xkqzwmplvnbrtdsa.ml/payload</string>\n  <string name="fb">https://abcdefghijklmnop.pw/collect</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_09",
        "name": "TC-09: PII — RRN + Bank Account",
        "description": "Document scan containing Korean Resident Registration Number and bank account details",
        "manifest": "",
        "strings": "",
        "document_text": "고객 정보\n성명: 홍길동\n주민등록번호: 950101-1234567\n계좌번호: 12345678901234\n연락처: 010-1234-5678",
    },
    {
        "id": "tc_10",
        "name": "TC-10: PII — Credit Card + Email + Passport",
        "description": "Document containing credit card number, email address, and passport number (multi-type PII leak)",
        "manifest": "",
        "strings": "",
        "document_text": "Applicant: John Doe\nEmail: john.doe@example.com\nPassport: M12345678\nCredit Card: 4532015112830366\nExpiry: 03/2027",
    },
    {
        "id": "tc_11",
        "name": "TC-11: Voice Phishing (Vishing) Agent",
        "description": "Impersonates government authority (tax office/police), intercepts calls, harvests contact list for large-scale vishing campaigns",
        "manifest": '<manifest package="com.gov.tax.refund.assist">\n  <uses-permission android:name="android.permission.CALL_PHONE"/>\n  <uses-permission android:name="android.permission.READ_CONTACTS"/>\n  <uses-permission android:name="android.permission.PROCESS_OUTGOING_CALLS"/>\n  <uses-permission android:name="android.permission.RECORD_AUDIO"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="vishing_server">https://calltrack.ru/collect</string>\n  <string name="contact_upload">http://phonebook.evil.biz/harvest</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_12",
        "name": "TC-12: Ransomware Dropper + Keyguard Bypass",
        "description": "Encrypts external storage files and disables screen lock, then installs secondary payload via C2 server",
        "manifest": '<manifest package="com.file.cleaner.pro">\n  <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>\n  <uses-permission android:name="android.permission.INSTALL_PACKAGES"/>\n  <uses-permission android:name="android.permission.DISABLE_KEYGUARD"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="c2">http://203.0.113.99/ransom/drop</string>\n  <string name="payload">https://abc123xyzdef456.ngrok.io/payload.apk</string>\n  <string name="key_server">http://ransom-pay.top/key</string>\n</resources>',
        "document_text": "",
    },
    # ── TC-13 ~ TC-24: Extended Malicious Pattern Test Cases ─────────────────
    {
        "id": "tc_13",
        "name": "TC-13: Clipboard Spy via Accessibility",
        "description": "Abuses Accessibility Service to monitor clipboard content and exfiltrate passwords or OTPs copied by the user to attacker-controlled infrastructure",
        "manifest": '<manifest package="com.keyboard.helper.pro">\n  <uses-permission android:name="android.permission.BIND_ACCESSIBILITY_SERVICE"/>\n  <uses-permission android:name="android.permission.WRITE_SETTINGS"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="c2">http://clipboard-sync.biz/beacon</string>\n  <string name="exfil_api">https://data.paste-collect.xyz/upload</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_14",
        "name": "TC-14: Contact-Based SMS Phishing Bot",
        "description": "Harvests full contact list to send targeted phishing SMS to all contacts, amplifying social-engineering attack surface across the victim's network",
        "manifest": '<manifest package="com.sms.manager.lite">\n  <uses-permission android:name="android.permission.READ_SMS"/>\n  <uses-permission android:name="android.permission.READ_CONTACTS"/>\n  <uses-permission android:name="android.permission.RECEIVE_SMS"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="phish_gate">http://secure-login.cc/phish/track</string>\n  <string name="harvest_api">http://contact-collect.xyz/dump</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_15",
        "name": "TC-15: Live A/V Stream Exfiltrator",
        "description": "Streams live camera and microphone feeds to attacker server via reverse-proxy ngrok tunnel, bypassing firewall and NAT restrictions in real time",
        "manifest": '<manifest package="com.video.conference.lite">\n  <uses-permission android:name="android.permission.CAMERA"/>\n  <uses-permission android:name="android.permission.RECORD_AUDIO"/>\n  <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="stream_relay">https://a1b2c3d4e5f6g7h8.ngrok.io/stream</string>\n  <string name="backup_c2">https://av-exfil.top/upload</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_16",
        "name": "TC-16: Device Fingerprint & Identity Harvester",
        "description": "Collects IMEI, device ID, and account identifiers to build a persistent cross-platform tracking profile for large-scale credential stuffing and ad fraud",
        "manifest": '<manifest package="com.system.analytics.sdk">\n  <uses-permission android:name="android.permission.READ_PHONE_STATE"/>\n  <uses-permission android:name="android.permission.GET_ACCOUNTS"/>\n  <uses-permission android:name="android.permission.READ_CONTACTS"/>\n  <uses-permission android:name="android.permission.WRITE_SETTINGS"/>\n</manifest>',
        "strings": '<resources>\n  <string name="tracker_api">https://qxzmwplvnbrtdsa.cc/payload</string>\n  <string name="id_dump">http://fingerprint.collect.biz/track</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_17",
        "name": "TC-17: Call Recording RAT",
        "description": "Remote access trojan that records all phone calls, intercepts outgoing calls, and streams audio to a C2 server on a non-standard high port",
        "manifest": '<manifest package="com.call.recorder.free">\n  <uses-permission android:name="android.permission.RECORD_AUDIO"/>\n  <uses-permission android:name="android.permission.READ_CALL_LOG"/>\n  <uses-permission android:name="android.permission.PROCESS_OUTGOING_CALLS"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="rat_c2">http://195.123.220.47:9999/shell</string>\n  <string name="audio_dump">https://call-rat.ru/steal</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_18",
        "name": "TC-18: Multi-Stage Dropper + Keyguard Bypass",
        "description": "Downloads and silently installs secondary payloads via ngrok tunnel while bypassing device screen lock to maintain persistent access after reboot",
        "manifest": '<manifest package="com.phone.optimizer.boost">\n  <uses-permission android:name="android.permission.INSTALL_PACKAGES"/>\n  <uses-permission android:name="android.permission.DISABLE_KEYGUARD"/>\n  <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="stage2_url">https://xyz9876abcdef123.ngrok.io/payload.apk</string>\n  <string name="drop_mirror">http://203.0.113.42/rat/drop</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_19",
        "name": "TC-19: Fake Tax Refund Phishing App",
        "description": "Masquerades as official tax refund authority, intercepts SMS OTPs, harvests account IDs, and redirects calls to attacker IVR to complete financial fraud",
        "manifest": '<manifest package="com.tax.refund.official.kr">\n  <uses-permission android:name="android.permission.CALL_PHONE"/>\n  <uses-permission android:name="android.permission.READ_SMS"/>\n  <uses-permission android:name="android.permission.RECEIVE_SMS"/>\n  <uses-permission android:name="android.permission.GET_ACCOUNTS"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="gate">https://tax-refund-kr.top/phish</string>\n  <string name="otp_relay">http://sms-intercept.pw/collect</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_20",
        "name": "TC-20: Precision Stalkerware v2 (Covert GPS)",
        "description": "Advanced stalkerware combining real-time GPS tracking with silent photo capture and contact exfiltration, routed through obfuscated high-risk TLD infrastructure",
        "manifest": '<manifest package="com.family.safety.tracker">\n  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>\n  <uses-permission android:name="android.permission.CAMERA"/>\n  <uses-permission android:name="android.permission.READ_CONTACTS"/>\n  <uses-permission android:name="android.permission.RECORD_AUDIO"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="gps_relay">https://location-track.xyz/exfil</string>\n  <string name="photo_dump">https://silent-cam.ru/upload</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_21",
        "name": "TC-21: Enterprise Data Exfiltration Agent",
        "description": "Targets corporate devices to silently extract call history, contacts, account credentials, and documents for competitive intelligence or state-sponsored espionage",
        "manifest": '<manifest package="com.productivity.office.suite">\n  <uses-permission android:name="android.permission.READ_CONTACTS"/>\n  <uses-permission android:name="android.permission.GET_ACCOUNTS"/>\n  <uses-permission android:name="android.permission.READ_CALL_LOG"/>\n  <uses-permission android:name="android.permission.CAMERA"/>\n  <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>\n</manifest>',
        "strings": '<resources>\n  <string name="corp_exfil">https://bizdata-dump.biz/upload</string>\n  <string name="c2_backup">http://87.120.36.197/backdoor</string>\n  <string name="alt_c2">https://pqrstuvwxyz12345.cc/shell</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_22",
        "name": "TC-22: Obfuscated Multi-C2 Botnet Node",
        "description": "Bot client with redundant C2 channels using DGA domains, IP direct access, encoded endpoints, and ngrok tunnels to evade static detection and maintain persistent control",
        "manifest": '<manifest package="com.news.reader.daily">\n  <uses-permission android:name="android.permission.INTERNET"/>\n  <uses-permission android:name="android.permission.WRITE_SETTINGS"/>\n  <uses-permission android:name="android.permission.RECEIVE_SMS"/>\n</manifest>',
        "strings": '<resources>\n  <string name="c2_primary">http://10.0.0.1:1337/cnc</string>\n  <string name="c2_dga">https://mnbvcxzlkjhgfds.ml/beacon</string>\n  <string name="c2_enc">https://api.update-cdn.tk/auth%2F%62%65%61%63%6F%6E%2Fpayload</string>\n  <string name="c2_ngrok">https://abcdef123456789.ngrok.io/shell</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_23",
        "name": "TC-23: PII — Employee HR Database Leak",
        "description": "HR database export containing full employee PII including resident registration numbers, corporate email addresses, and bank account details for direct payroll fraud",
        "manifest": "",
        "strings": "",
        "document_text": "HR Personnel Record — CONFIDENTIAL\nEmployee: 김민준 (Kim Minjun)\nEmployee ID: EMP-2024-0891\nRRN: 880315-1038291\nCorporate Email: minjun.kim@corp.co.kr\nBank Account: 110501123456789\nDepartment: Engineering\n\nEmployee: 이지영 (Lee Jiyoung)\nRRN: 921107-2654321\nEmail: jiyoung.lee@corp.co.kr\nAccount: 35201127744039",
    },
    {
        "id": "tc_24",
        "name": "TC-24: PII — Medical Patient Record",
        "description": "Hospital patient record containing comprehensive PII — RRN, passport, credit card for billing, and email — exposing the patient to identity theft and financial fraud",
        "manifest": "",
        "strings": "",
        "document_text": "Patient Record — CONFIDENTIAL\nName: Park Soomin\nRRN: 750620-1234567\nPassport No: M98765432\nInsurance Card: 4916338506082832\nEmail: soomin.park@gmail.com\nEmergency Contact Bank: 88901234567890\nDiagnosis: [REDACTED]\nAdmission Date: 2026-03-15",
    },
    {
        "id": "tc_25",
        "name": "TC-25: Multi-Stage PowerShell Dropper",
        "description": "App masquerading as a system tool that fetches and executes a PowerShell-based secondary payload from a public code hosting service",
        "manifest": '<manifest package="com.windows.compatibility.layer">\n  <uses-permission android:name="android.permission.INTERNET"/>\n  <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>\n</manifest>',
        "strings": '<resources>\n  <string name="update_script">https://raw.githubusercontent.com/evil-ops/scripts/main/rev_shell.ps1</string>\n  <string name="c2_relay">https://bit.ly/secure-tunnel-2026</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_26",
        "name": "TC-26: Private Photo & Video Exfiltrator",
        "description": "Malicious gallery app requesting broad media access to silently upload private user photos and videos to a high-risk TLD server",
        "manifest": '<manifest package="com.pro.gallery.vault">\n  <uses-permission android:name="android.permission.READ_MEDIA_IMAGES"/>\n  <uses-permission android:name="android.permission.READ_MEDIA_VIDEO"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="upload_server">http://cloud-storage-pro.xyz/v1/sync</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_27",
        "name": "TC-27: Background GPS Stalkerware (Advanced)",
        "description": "Stealthy stalkerware that tracks precise location in the background and uploads movement history to an obfuscated DGA domain",
        "manifest": '<manifest package="com.battery.saver.plus">\n  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>\n  <uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="telemetry">https://asdfghjklqwerty.top/report</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_28",
        "name": "TC-28: Ransomware with Full Storage Access",
        "description": "Ransomware requesting MANAGE_EXTERNAL_STORAGE to encrypt all user files (including documents and downloads) while disabling screen lock",
        "manifest": '<manifest package="com.disk.analyzer.utility">\n  <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE"/>\n  <uses-permission android:name="android.permission.DISABLE_KEYGUARD"/>\n  <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>',
        "strings": '<resources>\n  <string name="c2">http://185.120.220.10:8080/ransom</string>\n  <string name="payment_site">https://decrypt-my-files.cc/pay</string>\n</resources>',
        "document_text": "",
    },
    {
        "id": "tc_29",
        "name": "TC-29: PII — Real Estate Contract Leak",
        "description": "Scanned real estate contract containing buyer/seller PII, RRNs, bank account for deposit, and detailed address information",
        "manifest": "",
        "strings": "",
        "document_text": "부동산 매매 계약서\n매도인: 최영희\n주민등록번호: 600510-2345678\n주소: 서울특별시 강남구 역삼동 123-45\n계좌번호: 국민은행 09876543210987\n\n매수인: 박철수\n주민등록번호: 821212-1234567\n연락처: 010-9988-7766\n이메일: chulsoo.park@gmail.com",
    },
    {
        "id": "tc_30",
        "name": "TC-30: Comprehensive Identity Theft Document",
        "description": "Document containing multiple PII types: Passport, Credit Card, Email, and Resident Registration Number",
        "manifest": "",
        "strings": "",
        "document_text": "Identity Verification Form\nFull Name: Alice Winston\nRRN: 900725-2019382\nPassport Number: P102938475\nPersonal Email: alice.winston@outlook.com\nCredit Card for Verification: 5520112233445566\nBilling Address: 742 Evergreen Terrace, Springfield",
    },
]

class SecurityAuditRequest(BaseModel):
    manifest: str = ""
    strings: str = ""
    document_text: str = ""

@app.post("/api/security/audit")
def security_audit(req: SecurityAuditRequest):
    perm_findings = []
    for perm_name, meta in _DANGEROUS_PERMISSIONS.items():
        pattern = rf"android\.permission\.{_re.escape(perm_name)}"
        if _re.search(pattern, req.manifest):
            perm_findings.append({"permission": f"android.permission.{perm_name}", "score": meta["score"], "reason": meta["reason"]})

    url_findings = []
    for compiled, description, score in _SUSPICIOUS_URL_PATTERNS:
        for match in compiled.findall(req.strings):
            url_findings.append({"url": match, "score": score, "reason": description})

    perm_score = sum(f["score"] for f in perm_findings)
    url_score = sum(f["score"] for f in url_findings)
    total_score = min(perm_score + url_score, 100)
    threat_level = "CRITICAL" if total_score >= 70 else "WARNING" if total_score >= 40 else "SAFE"

    pi_findings = []
    for label, pat in _SENSITIVE_PI_PATTERNS.items():
        if _re.search(pat, req.document_text):
            pi_findings.append(f"{label} detected")

    return {
        "apk_analysis": {
            "threat_level": threat_level,
            "total_score": total_score,
            "score_breakdown": {"permission_score": perm_score, "url_score": url_score},
            "permission_findings": perm_findings,
            "url_findings": url_findings,
            "summary": f"{len(perm_findings)} dangerous permission(s) and {len(url_findings)} suspicious URL(s) detected.",
        },
        "pi_analysis": {
            "risk": "CRITICAL" if pi_findings else "SAFE",
            "encryption": "RSA-OAEP + AES-256" if pi_findings else "None",
            "details": pi_findings,
        },
    }

@app.get("/api/security/test-cases")
def get_security_test_cases():
    return SECURITY_TEST_CASES

# ── PoC v2-2 & v2-3 ─────────────────────────────────────────────────────────
# These specific patent modules have been moved to /pocs/poc_server.py
# to separate pure research/patent code from AI OS core logic.

@app.websocket("/ws/file-tree")
async def websocket_file_tree(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        tree = build_tree_from_qdrant()
        await websocket.send_json({"type": "tree", "tree": tree})
        while True:
            await websocket.send_json({"type": "ping"})
            await asyncio.sleep(30)
    except Exception:
        manager.disconnect(websocket)
