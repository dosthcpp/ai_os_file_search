from fastapi import FastAPI
from contextlib import asynccontextmanager
from pydantic import BaseModel
# import chromadb
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

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
