from typing import List
from fastapi import FastAPI
from contextlib import asynccontextmanager
from pydantic import BaseModel
import difflib
# import chromadb
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from fastapi.responses import HTMLResponse
from .diff_store import save_diff, get_diff

DIFF_STORE = {}  # path → diff lines

client = QdrantClient(url="https://qdrant.drakedognas.synology.me", port=443, https=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    collections = client.get_collections().collections
    names = {c.name for c in collections}

    if "files" not in names:
        client.create_collection(
            collection_name="files",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

    yield  # ⬅️ 여기서부터 request 처리

    # shutdown (필요하면)
    # client.close()

app = FastAPI(lifespan=lifespan)

# client = chromadb.Client()
# collection = client.create_collection("files")

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

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
def generate_diff(payload: DiffPayload):
    old_lines = payload.old_text.splitlines()
    new_lines = payload.new_text.splitlines()

    html = difflib.HtmlDiff().make_file(
        old_lines,
        new_lines,
        fromdesc="Before",
        todesc="After"
    )

    save_diff(payload.path, html)
    return {"ok": True}

@app.get("/api/diff", response_class=HTMLResponse)
def view_diff(path: str):
    html = get_diff(path)
    if not html:
        return "<h3>No diff</h3>"
    
    html = f"""
        <html>
        <head>
        <style>
        table.diff {{ font-family: monospace; font-size: 13px; }}
        .diff_add {{ background-color: #e6ffec; }}
        .diff_sub {{ background-color: #ffeef0; }}
        .diff_chg {{ background-color: #fff5b1; }}
        </style>
        </head>
        <body>
        {html}
        </body>
        </html>
    """

    return html