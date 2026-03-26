"""
AI OS — Search API

FastAPI server that provides:
  - Natural-language semantic search over indexed file chunks (ChromaDB)
  - File change tracking and version history
  - WebSocket broadcasts for real-time file-tree updates
  - Watch-path management persisted to config/settings.json
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from time import time as now
from typing import List, Optional
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

# Add packages/core to path so we can import the shared embedder
sys.path.insert(0, str(ROOT_DIR / "packages" / "core"))
from embedder import get_embedding as _openai_embed, EMBEDDING_DIM  # noqa: E402

# ── settings (persisted to disk) ──────────────────────────────────────────────

def load_settings() -> dict:
    """Load settings from JSON file; return defaults if file is missing."""
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    return {"watch_paths": [], "max_file_size_mb": 2, "server_url": "http://127.0.0.1:8000"}


def save_settings(settings: dict):
    """Persist settings dict to JSON file, creating parent dirs if needed."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ── ChromaDB (local persistent) ───────────────────────────────────────────────

_chroma: Optional[chromadb.PersistentClient] = None


def get_chroma() -> chromadb.PersistentClient:
    """Return the singleton ChromaDB persistent client."""
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
    # Metadata-filtered lookups only — no semantic search on this collection
    return get_chroma().get_or_create_collection("file_changes")


def _col_diffs():
    return get_chroma().get_or_create_collection("file_diffs", metadata={"hnsw:space": "cosine"})


# ── embedding (lazy, backed by OpenAI) ────────────────────────────────────────

def _embed(text: str) -> list[float]:
    """Return the OpenAI embedding vector for *text*."""
    return _openai_embed(text)


# ── WebSocket connection manager ──────────────────────────────────────────────

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

# ── file-tree helpers ─────────────────────────────────────────────────────────

def _build_tree(file_metas: list[dict]) -> dict:
    """Convert a flat list of file metadata dicts into a nested directory tree."""
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
    """Return the most-recent change record for each tracked file path."""
    result = _col_changes().get(include=["metadatas"])
    latest: dict[str, dict] = {}
    for meta in (result["metadatas"] or []):
        path = meta["path"]
        ts = meta["timestamp"]
        if path not in latest or ts > latest[path]["timestamp"]:
            latest[path] = meta
    return list(latest.values())


async def _notify_file_change(action: str, path: str, node: Optional[dict] = None):
    await manager.broadcast({"type": "file-changed", "action": action, "path": path, "node": node})


async def _notify_tree_update():
    tree = _build_tree(_latest_file_changes())
    await manager.broadcast({"type": "tree", "tree": tree})


# ── lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[START] AI OS Search API starting...", flush=True)
    # Ensure all collections exist before serving requests
    _col_files(); _col_versions(); _col_changes(); _col_diffs()
    print("[OK] ChromaDB collections ready", flush=True)
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
    node: Optional[dict] = None


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


# ── health check ──────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "embed_model_loaded": True}


# ── watch-path management (persisted) ─────────────────────────────────────────

@app.get("/api/watch-paths")
def get_watch_paths():
    return load_settings().get("watch_paths", [])


@app.post("/api/watch-path")
def add_watch_path(data: PathData):
    p = Path(data.path)
    if not p.is_dir():
        return {"ok": False, "error": "Directory does not exist"}
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


# ── chunk upsert / delete ─────────────────────────────────────────────────────

@app.post("/api/chunks/upsert")
def upsert_chunk(data: ChunkData):
    # Only scalar metadata types are supported by ChromaDB
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


# ── semantic search ───────────────────────────────────────────────────────────

@app.get("/api/search")
def search(
    q: str = Query(..., description="Natural-language search query"),
    n: int = Query(5, ge=1, le=50, description="Number of results to return"),
    collection: str = Query("files", description="Collection to search: files | file_versions | file_diffs"),
):
    """
    Embed *q* with OpenAI and run a cosine-similarity query against the
    specified ChromaDB collection.
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


# ── diff storage ──────────────────────────────────────────────────────────────

@app.post("/api/diff")
def save_diff(payload: DiffPayload):
    combined = payload.old_text + "\n" + payload.new_text
    vector = _embed(combined[:2000])
    # Use file path as the document ID so only the latest diff is kept per file
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


# ── file change events ────────────────────────────────────────────────────────

@app.post("/api/file-change")
async def record_file_change(payload: FileChangePayload):
    # Store a zero-vector placeholder — this collection is queried by metadata only
    _col_changes().add(
        ids=[str(uuid4())],
        embeddings=[[0.0] * EMBEDDING_DIM],
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


# ── file version storage ──────────────────────────────────────────────────────

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
    """Return the latest version metadata for every tracked file."""
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


# ── WebSocket: live file-tree ─────────────────────────────────────────────────

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
