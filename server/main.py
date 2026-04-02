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
