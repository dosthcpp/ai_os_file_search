import os
import json
import hashlib
import os
import json
import time
from text_extractor import extract_text
from embedder import get_embedding
from utils import load_state, save_state, update_state, handle_deleted_files, chunk_id_to_uuid, compute_diff, is_temp_file
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from chunker import chunk_text
from embedder import get_embedding
from client import upload_chunk, delete_chunks, upload_file, send_diff

with open("config.json") as f:
    config = json.load(f)

SCAN_PATHS = config["scan_paths"]
MAX_SIZE = config["max_file_size_mb"] * 1024 * 1024

def file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def index_file(path):
    if is_temp_file(path):
        return
    
    if not os.path.exists(path):
        return

    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return
    
    if stat.st_size > MAX_SIZE:
        return
    
    prev_state = load_state().get(path)
    old_text = prev_state.get("text") if prev_state else ""

    text = extract_text(path)
    if not text:
        return

    chunks = chunk_text(text)
    current_hash = file_hash(path)

    diff = compute_diff(old_text, text) if old_text else []

    chunk_ids = []

    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk)
        logical_id = f"{file_hash(path)}_{i}"
        chunk_id = chunk_id_to_uuid(logical_id)
        chunk_ids.append(chunk_id)

        # ✅ 서버 API 호출
        upload_chunk(
            chunk_id=chunk_id,
            vector=emb,
            payload={
                "path": path,
                "chunk_index": i,
                "text": chunk[:300]
            }
        )

    update_state(path, current_hash, chunk_ids, stat, text)

    if diff:
        send_diff(
            path=path,
            old_text=old_text or "",
            new_text=text
        )

def handle_file_delete(path: str):
    state = load_state()
    info = state.get(path)

    # 이미 인덱싱된 적 없는 파일이면 무시
    if not info:
        return

    chunk_ids = info.get("chunks", [])
    if chunk_ids:
        delete_chunks(chunk_ids)
        print(f"Deleted chunks for: {path}")

    # 로컬 상태에서도 제거
    state.pop(path, None)
    save_state(state)

class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        if is_temp_file(event.src_path):
            return
        index_file(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            return
        if is_temp_file(event.src_path):
            return
        index_file(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        handle_file_delete(event.src_path)

def start_watchdog():
    observer = Observer()
    handler = FileChangeHandler()

    for path in SCAN_PATHS:
        observer.schedule(handler, path, recursive=True)

    observer.start()
    print("Watching file changes...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

def scan():
    prev_state = load_state()
    new_state = {}

    for base in SCAN_PATHS:
        for root, dirs, files in os.walk(base):
            for file in files:
                full_path = os.path.join(root, file)

                try:
                    stat = os.stat(full_path)
                except FileNotFoundError:
                    continue

                if stat.st_size > MAX_SIZE:
                    continue

                prev = prev_state.get(full_path)
                current_hash = file_hash(full_path)

                # 🔹 변화 없음 → skip
                if prev and prev["hash"] == current_hash:
                    new_state[full_path] = prev
                    continue

                # 🔥 신규 or 변경된 파일만 여기로 옴
                text = extract_text(full_path)
                if not text:
                    continue

                summary = text[:300]
                embedding = get_embedding(summary)

                upload_file(
                    path=full_path,
                    summary=summary,
                    embedding=embedding,
                    hash=current_hash
                )

                new_state[full_path] = {
                    "hash": current_hash,
                    "mtime": stat.st_mtime,
                    "size": stat.st_size
                }

    handle_deleted_files(prev_state, new_state)

    # 🔥 상태 저장
    save_state(new_state)

if __name__ == "__main__":
    scan()
    start_watchdog()
