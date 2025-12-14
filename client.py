import requests
import json

with open("config.json") as f:
    config = json.load(f)

SERVER_URL = config["server_url"]

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