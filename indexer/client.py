import requests
import json
import time
import os

BASE_PATH = os.getcwd()

with open(f"{BASE_PATH}/indexer/config.json") as f:
    config = json.load(f)

SERVER_URL = config["server_url"]

def wait_for_server(url=f"{SERVER_URL}/api/health", timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                print("API server is ready")
                return True
            else:
                print("API server is not ready, retrying...")
        except requests.RequestException:
            print("RequestException occurred, retrying...")
            pass
        time.sleep(0.5)
    raise RuntimeError("API server not ready")

def fetch_watch_paths():
    res = requests.get(f"{SERVER_URL}/api/watch-paths")
    return res.json()

def upload_file(path, summary, embedding, hash):
    payload = {
        "path": path,
        "summary": summary,
        "embedding": embedding,
        "hash": hash
    }

    try:
        res = requests.post(f"{SERVER_URL}/api/files/index", json=payload)
        print("Uploaded:", path, res.status_code)
    except Exception as e:
        print("Upload failed:", path, "reason: ", e)

def delete_chunks(chunk_ids):
    requests.post(
        f"{SERVER_URL}/api/delete",
        json=chunk_ids
    )

def upload_chunk(
    chunk_id: str,
    vector: list[float],
    payload: dict
):
    res = requests.post(
        f"{SERVER_URL}/api/chunks/upsert",
        json={
            "id": chunk_id,
            "vector": vector,
            "payload": payload
        },
        timeout=10
    )
    res.raise_for_status()

def send_diff(path: str, old_text: str, new_text: str):
    res = requests.post(
        f"{SERVER_URL}/api/diff",
        json={
            "path": path,
            "old_text": old_text,
            "new_text": new_text
        },
        timeout=10
    )
    res.raise_for_status()

def build_node(path: str):
    stat = os.stat(path)

    return {
        "name": os.path.basename(path),
        "path": path,
        "type": "dir" if os.path.isdir(path) else "file",
        "size": stat.st_size,
        "modified": stat.st_mtime
    }

def send_file_change(path, status):
    payload = {
        "path": path,
        "status": status,
        "timestamp": time.time(),
    }

    if status != "deleted":
        payload["node"] = build_node(path)

    requests.post(
        f"{SERVER_URL}/api/file-change",
        json=payload,
        timeout=5
    )

def save_file_change(path, version, diff, summary, vector, _hash, change_type):
    payload = {
        "path": path,
        "version": version,
        "diff": diff,
        "summary": summary,
        "vector": vector,
        "hash": _hash,
        "change_type": change_type
    }
    requests.post(
        f"{SERVER_URL}/api/save-file-version",
        json=payload,
        timeout=5
    )