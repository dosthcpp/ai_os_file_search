import os
import json
import hashlib
from text_extractor import extract_text
from embedder import get_embedding
from uploader import upload_file

with open("config.json") as f:
    config = json.load(f)

SCAN_PATHS = config["scan_paths"]
MAX_SIZE = config["max_file_size_mb"] * 1024 * 1024

def file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def scan():
    for base in SCAN_PATHS:
        for root, dirs, files in os.walk(base):
            for file in files:
                full_path = os.path.join(root, file)

                if os.path.getsize(full_path) > MAX_SIZE:
                    continue

                text = extract_text(full_path)
                if not text:
                    continue

                summary = text[:300]  
                embedding = get_embedding(summary)
                hash_value = file_hash(full_path)

                upload_file(
                    path=full_path,
                    summary=summary,
                    embedding=embedding,
                    hash=hash_value
                )

if __name__ == "__main__":
    scan()
