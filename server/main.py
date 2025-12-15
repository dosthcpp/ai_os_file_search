import asyncio
from contextlib import asynccontextmanager
from enum import Enum
from time import time
from typing import List
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from qdrant_client.models import VectorParams, Distance
# import chromadb
from sentence_transformers import SentenceTransformer
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect, WebSocket

client = QdrantClient(url="https://qdrant.drakedognas.synology.me", port=443, https=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

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

        # 🔥 죽은 소켓 정리
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
        limit=50  # 충분히 크게
    )

    if not points:
        return None

    # timestamp 기준 최신 1개 선택
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
    """
    Qdrant에 저장된 FILE_CHANGE / DIFF 정보를 기반으로
    프론트에서 쓰는 파일 트리 구조 생성
    """
    records = client.scroll(
        collection_name="file_changes",
        with_payload=True,
        limit=10_000
    )[0]

    changes = [r.payload for r in records]

    return build_tree(changes)

async def notify_tree_update():
    tree = build_tree_from_qdrant()  # 네 기존 로직
    await manager.broadcast({
        "type": "tree",
        "tree": tree
    })

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

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

class ChunkData(BaseModel):
    id: str
    vector: list[float]
    payload: dict

class DiffPayload(BaseModel):
    path: str
    old_text: str
    new_text: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    app.state.loop = asyncio.get_running_loop()
    collections = client.get_collections().collections
    names = {c.name for c in collections}

    # event_handler = FileChangeHandler()
    # observer = Observer()
    # observer.schedule(event_handler, WATCH_PATH, recursive=True)
    # observer.start()
    # app.state.observer = observer

    if "files" not in names:
        client.create_collection(
            collection_name="files",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

    if "file_changes" not in names:
        client.create_collection(
            collection_name="file_changes",
            vectors_config=VectorParams(size=1, distance=Distance.COSINE)
        )

    if "file_diffs" not in names:
        client.create_collection(
            collection_name="file_diffs",
            vectors_config=VectorParams(size=1, distance=Distance.COSINE)
        )

    yield  # ⬅️ 여기서부터 request 처리

    # shutdown (필요하면)
    # observer.stop()
    # observer.join()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/files/index")
def index_file(data: FileData):
    # collection.add(
    #     ids=[data.hash],
    #     metadatas=[{"path": data.path, "summary": data.summary}],
    #     embeddings=[data.embedding]
    # )
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

@app.get("/api/search")
def search(q: str):
    query_emb = embed_model.encode(q).tolist()

    result = client.query_points(
        collection_name="files",
        prefetch=[],                 # optional
        query=query_emb,             # 🔥 핵심
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
    client.delete(
        collection_name="files",
        points_selector=ids
    )
    return {"deleted": len(ids)}

@app.post("/api/chunks/upsert")
def upsert_chunk(data: ChunkData):
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
    client.upsert(
        collection_name="file_diffs",
        points=[PointStruct(
            id=str(uuid4()),
            vector=[0.0],
            payload={
                "path": payload.path,
                "old_text": payload.old_text,
                "new_text": payload.new_text,
                "timestamp": time()
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

@app.post("/api/file-change")
async def record_file_change(payload: FileChangePayload):
    point = PointStruct(
        id=str(uuid4()),
        vector=[0.0],  # dummy vector
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
        payload.node   # 그대로 WS로 전달
    )

    # 2️⃣ 🔥 tree 전체 재전송 (핵심)
    await notify_tree_update()

    return {"ok": True}

@app.get("/api/changed-files")
def get_changed_files():
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

@app.websocket("/ws/file-tree")
async def websocket_file_tree(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # 🔥 최초 1회 tree 전송
        tree = build_tree_from_qdrant()
        await websocket.send_json({
            "type": "tree",
            "tree": tree
        })

        while True:
            await websocket.send_json({"type": "ping"})
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print("ws error:", e)
        manager.disconnect(websocket)




