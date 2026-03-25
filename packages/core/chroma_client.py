import os
from pathlib import Path

import chromadb

ROOT_DIR = Path(__file__).resolve().parents[2]
CHROMA_PATH = str(ROOT_DIR / "data" / "chroma")

_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client
