import asyncio
import sys
from contextlib import asynccontextmanager
from enum import Enum
from time import time as now
from typing import List
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from qdrant_client.models import VectorParams, Distance
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect, WebSocket

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
    await manager.broadcast({
        "type": "file-changed",
        "action": action,
        "path": path,
        "node": node
    })

def get_latest_diff(path: str):
    client = get_client()
    points, _ = client.scroll(
        collection_name="file_diffs",
        with_payload=True,
        scroll_filter={
            "must": [
                {
                    "key": "path",
                    "match": {"value": path}
                }
            ]
        },
        limit=50
    )

    if not points:
        return None

    latest = max(points, key=lambda p: p.payload["timestamp"])
    return latest.payload

def build_tree(file_changes: list[dict]):
    root = {}

    for meta in file_changes:
        path = meta["path"]
        status = meta["status"]

        parts = path.replace("\\", "/").split("/")
        cur = root

        for part in parts[:-1]:
            cur = cur.setdefault(part, {})

        cur[parts[-1]] = {
            "_file": True,
            "status": status,
            "path": path
        }

    def to_node(name, obj):
        if "_file" in obj:
            return {
                "name": name,
                "type": "file",
                "status": obj["status"],
                "path": obj["path"]
            }

        return {
            "name": name,
            "type": "dir",
            "children": [
                to_node(k, v) for k, v in obj.items()
            ]
        }

    return {
        "name": "root",
        "type": "dir",
        "children": [
            to_node(k, v) for k, v in root.items()
        ]
    }

def build_tree_from_qdrant():
    client = get_client()
    records = client.scroll(
        collection_name="file_changes",
        with_payload=True,
        limit=10_000
    )[0]

    changes = [r.payload for r in records]
    return build_tree(changes)

async def notify_tree_update():
    tree = build_tree_from_qdrant()
    await manager.broadcast({
        "type": "tree",
        "tree": tree
    })

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

# 🔥 백그라운드 초기화 태스크
async def init_collections():
    """백그라운드에서 컬렉션 초기화"""
    print("[INFO] Initializing Qdrant collections...")
    client = get_client()

    collections = client.get_collections().collections
    names = {c.name for c in collections}

    if "files" not in names:
        client.create_collection(
            collection_name="files",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print("[OK] Created 'files' collection")

    if "file_changes" not in names:
        client.create_collection(
            collection_name="file_changes",
            vectors_config=VectorParams(size=1, distance=Distance.COSINE)
            # vectors_config=None
        )
        print("[OK] Created 'file_changes' collection")

    if "file_diffs" not in names:
        client.create_collection(
            collection_name="file_diffs",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print("[OK] Created 'file_diffs' collection")

    if "file_versions" not in names:
        client.create_collection(
            collection_name="file_versions",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print("[OK] Created 'file_versions' collection")

    print("[OK] Qdrant collections ready")

async def warmup_model():
    """백그라운드에서 임베딩 모델 로드"""
    await asyncio.sleep(0.1)  # 서버 시작 우선순위
    get_embed_model()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[START] Server starting...")

    # 백그라운드 태스크로 실행 (블로킹 안 함)
    asyncio.create_task(init_collections())
    asyncio.create_task(warmup_model())

    print("[READY] Server ready (background tasks running)")
    yield
    print("[STOP] Server shutting down")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "embed_model_loaded": embed_model is not None,
        "client_initialized": client is not None
    }

WATCH_PATHS = []
class PathData(BaseModel):
    path: str

@app.post("/api/watch-path")
def set_watch_path(path: PathData):
    try:
        p = Path(path.path)
        if p.is_dir():
            WATCH_PATHS.append(path.path)
            return {"ok": True}
        else:
            return {"ok": False}
    except OSError:
        return {"ok": False}
    except ValueError:
        return {"ok": False}


@app.get("/api/watch-paths")
def get_watch_path():
    return WATCH_PATHS

@app.get("/api/files")
def list_files():
    points, _ = client.scroll(
        collection_name="file_versions",
        with_payload=True,
        with_vectors=False,
        limit=10_000
    )

    latest = {}

    for p in points:
        path = p.payload["path"]
        v = p.payload["version"]

        if path not in latest or v > latest[path]["version"]:
            latest[path] = {
                "path": path,
                "version": v,
                "timestamp": p.payload["timestamp"],
            }

    return list(latest.values())

@app.post("/api/files/index")
def index_file(data: FileData):
    client = get_client()
    client.upsert(
        collection_name="files",
        points=[
            {
                "id": data.hash,
                "vector": data.embedding,
                "payload": {"path": data.path, "summary": data.summary}
            }
        ]
    )
    return {"status": "ok"}

@app.get("/api/files/versions")
def list_file_versions(path: str):
    points, _ = client.scroll(
        collection_name="file_versions",
        scroll_filter={
            "must": [
                {"key": "path", "match": {"value": path}}
            ]
        },
        with_payload=True,
        with_vectors=False,
        limit=100
    )

    return sorted(
        [
            {
                "version": p.payload["version"],
                "timestamp": p.payload["timestamp"],
                "change_type": p.payload["change_type"],
                "summary": p.payload["summary"],
            }
            for p in points
        ],
        key=lambda x: x["version"],
        reverse=True
    )

@app.get("/api/search")
def search(q: str):
    client = get_client()
    model = get_embed_model()  # 🔥 lazy loading

    query_emb = model.encode(q).tolist()

    result = client.query_points(
        collection_name="files",
        prefetch=[],
        query=query_emb,
        limit=5
    )

    return [
        {
            "score": point.score,
            "path": point.payload.get("path"),
            "summary": point.payload.get("summary")
        }
        for point in result.points
    ]

@app.post("/api/delete")
def delete_points(ids: List[str]):
    client = get_client()
    client.delete(
        collection_name="files",
        points_selector=ids
    )
    return {"deleted": len(ids)}

@app.post("/api/chunks/upsert")
def upsert_chunk(data: ChunkData):
    client = get_client()
    client.upsert(
        collection_name="files",
        points=[{
            "id": data.id,
            "vector": data.vector,
            "payload": data.payload
        }]
    )
    return {"ok": True}

@app.post("/api/diff")
def save_diff(payload: DiffPayload):
    global client
    client = get_client()

    model = get_embed_model()
    text = payload.old_text + "\n" + payload.new_text
    vector = model.encode(text).tolist()
    client.upsert(
        collection_name="file_diffs",
        points=[PointStruct(
            id=str(uuid4()),
            vector=vector,
            payload={
                "path": payload.path,
                "old_text": payload.old_text,
                "new_text": payload.new_text,
                "timestamp": now()
            }
        )]
    )
    return {"ok": True}

@app.get("/api/diff")
def get_diff(path: str):
    diff = get_latest_diff(path)
    if not diff:
        return {"path": path, "old_text": "", "new_text": ""}

    return {
        "path": path,
        "old_text": diff["old_text"],
        "new_text": diff["new_text"],
        "timestamp": diff["timestamp"]
    }

@app.get("/api/files/version/diff")
def get_version_diff(path: str, version: int):
    points, _ = client.scroll(
        collection_name="file_versions",
        scroll_filter={
            "must": [
                {"key": "path", "match": {"value": path}},
                {"key": "version", "match": {"value": version}},
            ]
        },
        with_payload=True,
        with_vectors=False,
        limit=1
    )

    if not points:
        return {"diff": ""}

    return {
        "diff": points[0].payload["diff"]
    }

@app.post("/api/file-change")
async def record_file_change(payload: FileChangePayload):
    client = get_client()
    point = PointStruct(
        id=str(uuid4()),
        vector=[0.0],
        payload={
            "path": payload.path,
            "status": payload.status,
            "timestamp": payload.timestamp,
        }
    )
    client.upsert(
        collection_name="file_changes",
        points=[point]
    )
    await notify_file_change(
        payload.status,
        payload.path,
        payload.node
    )
    await notify_tree_update()

    return {"ok": True}

@app.get("/api/changed-files")
def get_changed_files():
    client = get_client()
    points, _ = client.scroll(
        collection_name="file_changes",
        limit=100,
        with_payload=True
    )

    return sorted(
        [p.payload for p in points],
        key=lambda x: x["timestamp"],
        reverse=True
    )

def latest_file_changes():
    client = get_client()
    points, _ = client.scroll(
        collection_name="file_changes",
        with_payload=True,
        limit=1000
    )

    latest = {}
    for p in points:
        path = p.payload["path"]
        ts = p.payload["timestamp"]

        if path not in latest or ts > latest[path]["timestamp"]:
            latest[path] = p.payload

    return list(latest.values())

@app.get("/api/changed-files/tree")
def get_changed_files_tree():
    file_changes = latest_file_changes()
    return build_tree(file_changes)

@app.post("/api/save-file-version")
def save_file_version(
    data: FileVersionData
):
    client.upsert(
        collection_name="file_versions",
        points=[{
            # "id": f"file::{data.path}::v{data.version}",
            "id": str(uuid4()),
            "vector": list(map(float, data.vector)),
            "payload": {
                "path": data.path,
                "version": data.version,
                "hash": data.hash,
                "timestamp": now(),
                "change_type": data.change_type,
                "diff": data.diff,
                "summary": data.summary,
            }
        }]
    )

@app.websocket("/ws/file-tree")
async def websocket_file_tree(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        tree = build_tree_from_qdrant()
        await websocket.send_json({
            "type": "tree",
            "tree": tree
        })

        while True:
            try:
                await websocket.send_json({"type": "ping"})
                await asyncio.sleep(30)
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print("ws error:", e)
        manager.disconnect(websocket)