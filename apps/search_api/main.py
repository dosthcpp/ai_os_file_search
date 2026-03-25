"""
AI OS — Search API
ChromaDB 기반 자연어 검색 + 파일 인덱싱 게이트웨이
"""
import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from time import time as now
from typing import List
from uuid import uuid4

import chromadb
from fastapi import FastAPI, Query
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[2]
SETTINGS_FILE = ROOT_DIR / "config" / "settings.json"
CHROMA_PATH = str(ROOT_DIR / "data" / "chroma")

# ── settings (watch_paths 영속 저장) ─────────────────────────────────────────

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    return {"watch_paths": [], "max_file_size_mb": 2, "server_url": "http://127.0.0.1:8000"}


def save_settings(settings: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )

# ── ChromaDB ──────────────────────────────────────────────────────────────────

_chroma: chromadb.PersistentClient | None = None


def get_chroma() -> chromadb.PersistentClient:
    global _chroma
    if _chroma is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _chroma = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma


def _col_files():
    return get_chroma().get_or_create_collection("files", metadata={"hnsw:space": "cosine"})


def _col_versions():
    return get_chroma().get_or_create_collection("file_versions", metadata={"hnsw:space": "cosine"})


def _col_changes():
    # 메타데이터 필터링만 사용 — 의미 검색 없음
    return get_chroma().get_or_create_collection("file_changes")


def _col_diffs():
    return get_chroma().get_or_create_collection("file_diffs", metadata={"hnsw:space": "cosine"})


# ── embedding (lazy) ──────────────────────────────────────────────────────────
_embed_model = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        print("[LOAD] Loading embedding model...", flush=True)
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[OK] Embedding model loaded", flush=True)
    return _embed_model


def _embed(text: str) -> list[float]:
    return get_embed_model().encode(text).tolist()


# ── WebSocket ─────────────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        try:
            self.active.remove(ws)
        except ValueError:
            pass

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()

# ── tree builder ──────────────────────────────────────────────────────────────

def _build_tree(file_metas: list[dict]) -> dict:
    root: dict = {}
    for meta in file_metas:
        path = meta["path"]
        parts = path.replace("\\", "/").split("/")
        cur = root
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = {"_file": True, "status": meta["status"], "path": path}

    def to_node(name: str, obj: dict) -> dict:
        if "_file" in obj:
            return {"name": name, "type": "file", "status": obj["status"], "path": obj["path"]}
        return {"name": name, "type": "dir",
                "children": [to_node(k, v) for k, v in obj.items()]}

    return {"name": "root", "type": "dir",
            "children": [to_node(k, v) for k, v in root.items()]}


def _latest_file_changes() -> list[dict]:
    result = _col_changes().get(include=["metadatas"])
    latest: dict[str, dict] = {}
    for meta in (result["metadatas"] or []):
        path = meta["path"]
        ts = meta["timestamp"]
        if path not in latest or ts > latest[path]["timestamp"]:
            latest[path] = meta
    return list(latest.values())


async def _notify_file_change(action: str, path: str, node: dict | None = None):
    await manager.broadcast({"type": "file-changed", "action": action, "path": path, "node": node})


async def _notify_tree_update():
    tree = _build_tree(_latest_file_changes())
    await manager.broadcast({"type": "tree", "tree": tree})


# ── lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[START] AI OS Search API starting...", flush=True)
    # ChromaDB 컬렉션 초기화
    _col_files(); _col_versions(); _col_changes(); _col_diffs()
    print("[OK] ChromaDB collections ready", flush=True)
    # 임베딩 모델 백그라운드 로드
    asyncio.create_task(asyncio.to_thread(get_embed_model))
    print("[READY] Server ready", flush=True)
    yield
    print("[STOP] Server shutting down", flush=True)


app = FastAPI(title="AI OS Search API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ── Pydantic models ───────────────────────────────────────────────────────────

class FileStatus(str, Enum):
    added = "added"
    modified = "modified"
    deleted = "deleted"


class FileChangePayload(BaseModel):
    path: str
    status: FileStatus
    timestamp: float
    node: dict | None = None


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


class PathData(BaseModel):
    path: str


# ── 상태 확인 ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "embed_model_loaded": _embed_model is not None}


# ── 감시 경로 (영속 저장) ──────────────────────────────────────────────────────

@app.get("/api/watch-paths")
def get_watch_paths():
    return load_settings().get("watch_paths", [])


@app.post("/api/watch-path")
def add_watch_path(data: PathData):
    p = Path(data.path)
    if not p.is_dir():
        return {"ok": False, "error": "존재하지 않는 디렉토리입니다"}
    settings = load_settings()
    if data.path not in settings.setdefault("watch_paths", []):
        settings["watch_paths"].append(data.path)
        save_settings(settings)
    return {"ok": True}


@app.delete("/api/watch-path")
def remove_watch_path(data: PathData):
    settings = load_settings()
    settings["watch_paths"] = [p for p in settings.get("watch_paths", []) if p != data.path]
    save_settings(settings)
    return {"ok": True}


# ── 청크 업서트 / 삭제 ────────────────────────────────────────────────────────

@app.post("/api/chunks/upsert")
def upsert_chunk(data: ChunkData):
    safe_meta = {k: v for k, v in data.payload.items() if isinstance(v, (str, int, float, bool))}
    doc = data.payload.get("text") or data.payload.get("path", "")
    _col_files().upsert(
        ids=[data.id],
        embeddings=[data.vector],
        metadatas=[safe_meta],
        documents=[doc],
    )
    return {"ok": True}


@app.post("/api/delete")
def delete_chunks(ids: List[str]):
    _col_files().delete(ids=ids)
    return {"deleted": len(ids)}


# ── 자연어 검색 ───────────────────────────────────────────────────────────────

@app.get("/api/search")
def search(
    q: str = Query(..., description="자연어 검색어"),
    n: int = Query(5, ge=1, le=50, description="결과 개수"),
    collection: str = Query("files", description="검색 대상 컬렉션"),
):
    """
    자연어 쿼리를 벡터로 변환해 ChromaDB에서 의미 기반 검색합니다.
    collection: files | file_versions | file_diffs
    """
    col_map = {"files": _col_files, "file_versions": _col_versions, "file_diffs": _col_diffs}
    col_fn = col_map.get(collection, _col_files)

    query_emb = _embed(q)
    results = col_fn().query(
        query_embeddings=[query_emb],
        n_results=n,
        include=["metadatas", "documents", "distances"],
    )

    return [
        {
            "score": round(1 - dist, 4),
            "path": meta.get("path"),
            "text": (doc or "")[:500],
            "chunk_index": meta.get("chunk_index"),
            "collection": collection,
        }
        for meta, doc, dist in zip(
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
        )
    ]


# ── diff 저장 / 조회 ──────────────────────────────────────────────────────────

@app.post("/api/diff")
def save_diff(payload: DiffPayload):
    combined = payload.old_text + "\n" + payload.new_text
    vector = _embed(combined[:2000])
    # path를 ID로 사용 → 파일당 최신 diff만 유지
    _col_diffs().upsert(
        ids=[payload.path],
        embeddings=[vector],
        metadatas=[{
            "path": payload.path,
            "timestamp": now(),
            "old_text": payload.old_text,
            "new_text": payload.new_text,
        }],
        documents=[combined[:1000]],
    )
    return {"ok": True}


@app.get("/api/diff")
def get_diff(path: str):
    result = _col_diffs().get(ids=[path], include=["metadatas"])
    if not result["ids"]:
        return {"path": path, "old_text": "", "new_text": ""}
    meta = result["metadatas"][0]
    return {
        "path": path,
        "old_text": meta.get("old_text", ""),
        "new_text": meta.get("new_text", ""),
        "timestamp": meta.get("timestamp", 0),
    }


# ── 파일 변경 이벤트 ──────────────────────────────────────────────────────────

@app.post("/api/file-change")
async def record_file_change(payload: FileChangePayload):
    _col_changes().add(
        ids=[str(uuid4())],
        embeddings=[[0.0] * 384],
        metadatas=[{
            "path": payload.path,
            "status": payload.status.value,
            "timestamp": payload.timestamp,
        }],
        documents=[payload.path],
    )
    await _notify_file_change(payload.status.value, payload.path, payload.node)
    await _notify_tree_update()
    return {"ok": True}


@app.get("/api/changed-files")
def get_changed_files():
    result = _col_changes().get(include=["metadatas"])
    return sorted(result["metadatas"] or [], key=lambda x: x["timestamp"], reverse=True)


@app.get("/api/changed-files/tree")
def get_changed_files_tree():
    return _build_tree(_latest_file_changes())


# ── 버전 저장 / 조회 ──────────────────────────────────────────────────────────

@app.post("/api/save-file-version")
def save_file_version(data: FileVersionData):
    _col_versions().upsert(
        ids=[str(uuid4())],
        embeddings=[list(map(float, data.vector))],
        metadatas=[{
            "path": data.path,
            "version": data.version,
            "hash": data.hash,
            "timestamp": now(),
            "change_type": data.change_type,
            "summary": data.summary,
            "diff": json.dumps(data.diff, ensure_ascii=False),
        }],
        documents=[data.summary],
    )
    return {"ok": True}


@app.get("/api/files")
def list_files():
    result = _col_versions().get(include=["metadatas"])
    latest: dict[str, dict] = {}
    for meta in (result["metadatas"] or []):
        path = meta["path"]
        v = meta["version"]
        if path not in latest or v > latest[path]["version"]:
            latest[path] = {"path": path, "version": v, "timestamp": meta["timestamp"]}
    return list(latest.values())


@app.get("/api/files/versions")
def list_file_versions(path: str):
    result = _col_versions().get(
        where={"path": {"$eq": path}},
        include=["metadatas"],
    )
    return sorted(
        [
            {
                "version": m["version"],
                "timestamp": m["timestamp"],
                "change_type": m["change_type"],
                "summary": m["summary"],
            }
            for m in (result["metadatas"] or [])
        ],
        key=lambda x: x["version"],
        reverse=True,
    )


@app.get("/api/files/version/diff")
def get_version_diff(path: str, version: int):
    result = _col_versions().get(
        where={"$and": [{"path": {"$eq": path}}, {"version": {"$eq": version}}]},
        include=["metadatas"],
    )
    if not result["ids"]:
        return {"diff": []}
    diff_raw = result["metadatas"][0].get("diff", "[]")
    return {"diff": json.loads(diff_raw)}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/file-tree")
async def websocket_file_tree(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        tree = _build_tree(_latest_file_changes())
        await websocket.send_json({"type": "tree", "tree": tree})
        while True:
            await websocket.send_json({"type": "ping"})
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print("WS error:", e, flush=True)
        manager.disconnect(websocket)
