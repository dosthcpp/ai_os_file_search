from fastapi import FastAPI
from pydantic import BaseModel
# import chromadb
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

def startup():
    client.recreate_collection(
        collection_name="files",
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

app = FastAPI(on_startup=startup)

# client = chromadb.Client()
client = QdrantClient(url="https://qdrant.drakedognas.synology.me")
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
    # results = collection.query(query_embeddings=[query_emb], n_results=5)
    results = client.search(
        collection_name="files",
        query_vector=query_emb,
        limit=5
    )
    return results
