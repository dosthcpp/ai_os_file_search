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
        res = requests.post(SERVER_URL, json=payload)
        print("Uploaded:", path, res.status_code)
    except:
        print("Upload failed:", path)
