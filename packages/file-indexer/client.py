import json
import os
import time
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parents[2]
SETTINGS_FILE = ROOT_DIR / "config" / "settings.json"


def _server_url() -> str:
    try:
        settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return settings.get("server_url", "http://127.0.0.1:8000")
    except Exception:
        return "http://127.0.0.1:8000"


def wait_for_server(timeout: int = 30):
    url = f"{_server_url()}/api/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                print("API server is ready", flush=True)
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError("API server not ready after 30s")


def fetch_watch_paths() -> list[str]:
    r = requests.get(f"{_server_url()}/api/watch-paths", timeout=5)
    return r.json()


def upload_chunk(chunk_id: str, vector: list[float], payload: dict):
    requests.post(
        f"{_server_url()}/api/chunks/upsert",
        json={"id": chunk_id, "vector": vector, "payload": payload},
        timeout=10,
    ).raise_for_status()


def delete_chunks(chunk_ids: list[str]):
    requests.post(
        f"{_server_url()}/api/delete",
        json=chunk_ids,
        timeout=10,
    )


def send_diff(path: str, old_text: str, new_text: str):
    requests.post(
        f"{_server_url()}/api/diff",
        json={"path": path, "old_text": old_text, "new_text": new_text},
        timeout=10,
    ).raise_for_status()


def send_file_change(path: str, status: str):
    payload = {"path": path, "status": status, "timestamp": time.time()}
    if status != "deleted" and os.path.exists(path):
        stat = os.stat(path)
        payload["node"] = {
            "name": os.path.basename(path),
            "path": path,
            "type": "file",
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }
    requests.post(f"{_server_url()}/api/file-change", json=payload, timeout=5)


def save_file_version(path: str, version: int, diff: list[str], summary: str,
                      vector: list[float], file_hash: str, change_type: str):
    requests.post(
        f"{_server_url()}/api/save-file-version",
        json={
            "path": path,
            "version": version,
            "diff": diff,
            "summary": summary,
            "vector": vector,
            "hash": file_hash,
            "change_type": change_type,
        },
        timeout=5,
    )


def upload_image_embedding(path: str, image_vector: list[float], file_hash: str):
    """
    Send a pre-computed CLIP image embedding to the search API.

    The API stores it in the 'images_clip' ChromaDB collection so it can be
    retrieved via GET /api/search/images.
    """
    requests.post(
        f"{_server_url()}/api/images/index",
        json={"path": path, "vector": image_vector, "hash": file_hash},
        timeout=10,
    ).raise_for_status()


def delete_image_embedding(path: str):
    """Remove a CLIP image embedding from the 'images_clip' collection."""
    requests.delete(
        f"{_server_url()}/api/images/index",
        json={"path": path},
        timeout=10,
    )
