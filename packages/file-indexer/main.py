"""
AI OS — File Indexer
파일 시스템을 감시하고 변경 내용을 search-api로 전송합니다.
"""
import hashlib
import os
import sys
import threading
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from chunker import chunk_text
from client import (
    delete_chunks,
    fetch_watch_paths,
    save_file_version,
    send_diff,
    send_file_change,
    upload_chunk,
    wait_for_server,
)
from text_extractor import extract_text
from utils import (
    chunk_id_to_uuid,
    compute_diff,
    ensure_state_file,
    is_temp_file,
    load_state,
    save_state,
    update_state,
)

# ── embedding (lazy) ──────────────────────────────────────────────────────────
_embed_model = None

def get_embedding(text: str) -> list[float]:
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model.encode(text).tolist()

# ── config ────────────────────────────────────────────────────────────────────
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SETTINGS_FILE = ROOT_DIR / "config" / "settings.json"


def max_file_size() -> int:
    try:
        s = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return s.get("max_file_size_mb", 2) * 1024 * 1024
    except Exception:
        return 2 * 1024 * 1024


# ── delete debounce ───────────────────────────────────────────────────────────
DELETE_DELAY = 1.0
_pending_deletes: dict[str, threading.Timer] = {}


def _cancel_pending_delete(path: str):
    t = _pending_deletes.pop(path, None)
    if t:
        t.cancel()


# ── inflight guard ────────────────────────────────────────────────────────────
INFLIGHT: set[str] = set()
INFLIGHT_LOCK = threading.Lock()

# ── scanning guard ────────────────────────────────────────────────────────────
SCANNING_PATHS: set[str] = set()
SCANNING_LOCK = threading.Lock()


# ── diff summary ──────────────────────────────────────────────────────────────
def _summarize_diff(diff: list[str], max_len: int = 200) -> str:
    added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    preview = " ".join(diff[:5])
    return f"Added {added} lines, removed {removed} lines. Changes: {preview[:max_len]}"


def _file_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ── core indexing logic ───────────────────────────────────────────────────────
def index_file(path: str, from_scan: bool = False):
    if is_temp_file(path) or not os.path.exists(path):
        return

    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return

    if stat.st_size > max_file_size():
        return

    if not from_scan:
        with SCANNING_LOCK:
            for p in SCANNING_PATHS:
                if path.startswith(p):
                    return

    with INFLIGHT_LOCK:
        if path in INFLIGHT:
            return
        INFLIGHT.add(path)

    try:
        current_hash = _file_hash(path)
        prev_state = load_state().get(path)

        is_new = prev_state is None
        is_modified = prev_state is not None and prev_state["hash"] != current_hash

        if not is_new and not is_modified:
            return

        old_text = prev_state.get("text", "") if prev_state else ""
        text = extract_text(path)
        if not text:
            return

        chunks = chunk_text(text)
        chunk_ids = []

        for i, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            chunk_id = chunk_id_to_uuid(f"{current_hash}_{i}")
            chunk_ids.append(chunk_id)
            upload_chunk(
                chunk_id=chunk_id,
                vector=emb,
                payload={"path": path, "chunk_index": i, "text": chunk[:300]},
            )

        diff = compute_diff(old_text, text)
        prev_version = prev_state.get("version", 0) if prev_state else 0
        new_version = prev_version + 1

        update_state(path=path, file_hash=current_hash, chunk_ids=chunk_ids,
                     stat=stat, text=text, version=new_version)

        if is_new:
            send_file_change(path, "added")
            save_file_version(path=path, version=new_version, diff=diff,
                              summary="Initial version",
                              vector=get_embedding("Initial version"),
                              file_hash=current_hash, change_type="added")

        elif is_modified and diff:
            summary = _summarize_diff(diff)
            send_file_change(path, "modified")
            save_file_version(path=path, version=new_version, diff=diff,
                              summary=summary,
                              vector=get_embedding(summary),
                              file_hash=current_hash, change_type="modified")
            send_diff(path=path, old_text=old_text, new_text=text)

    finally:
        with INFLIGHT_LOCK:
            INFLIGHT.discard(path)


def _handle_file_delete(path: str):
    state = load_state()
    info = state.get(path)
    if not info:
        return

    chunk_ids = info.get("chunks", [])
    if chunk_ids:
        delete_chunks(chunk_ids)

    # record deleted version
    save_file_version(
        path=path, version=info.get("version", 0) + 1,
        diff=["(file deleted)"], summary="File deleted",
        vector=get_embedding("File deleted"),
        file_hash=info.get("hash", ""), change_type="deleted",
    )

    state.pop(path, None)
    save_state(state)
    send_file_change(path, "deleted")
    print(f"Deleted: {path}", flush=True)


def _finalize_delete(path: str):
    if os.path.exists(path):
        return
    _handle_file_delete(path)
    _pending_deletes.pop(path, None)


def _delayed_index(path: str, delay: float = 0.3):
    def _run():
        if os.path.exists(path):
            index_file(path)
    threading.Timer(delay, _run).start()


# ── file system event handler ─────────────────────────────────────────────────
class FileChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or is_temp_file(event.src_path):
            return
        print("[EVT created]", event.src_path, flush=True)
        _cancel_pending_delete(event.src_path)
        _delayed_index(event.src_path)

    def on_modified(self, event):
        if event.is_directory or is_temp_file(event.src_path):
            return
        print("[EVT modified]", event.src_path, flush=True)
        _cancel_pending_delete(event.src_path)
        _delayed_index(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        path = event.src_path
        timer = threading.Timer(DELETE_DELAY, lambda: _finalize_delete(path))
        _pending_deletes[path] = timer
        timer.start()


# ── watchdog management ───────────────────────────────────────────────────────
_observer: Observer | None = None
_current_paths: set[str] = set()
_observer_lock = threading.Lock()
_handler = FileChangeHandler()


def _initial_scan(path: str):
    print("Initial scan:", path, flush=True)
    state_before = {k: v for k, v in load_state().items() if k.startswith(path)}

    with SCANNING_LOCK:
        SCANNING_PATHS.add(path)
    try:
        for root, _, files in os.walk(path):
            for name in files:
                index_file(os.path.join(root, name), from_scan=True)
    finally:
        with SCANNING_LOCK:
            SCANNING_PATHS.discard(path)

    state_after = load_state()

    # handle files deleted while indexer was offline
    deleted = set(state_before.keys()) - set(state_after.keys())
    for p in deleted:
        _handle_file_delete(p)


def _restart_watchdog(new_paths: set[str]):
    global _observer, _current_paths
    added = new_paths - _current_paths

    with _observer_lock:
        if _observer:
            _observer.stop()
            _observer.join()
        _observer = Observer()
        for p in new_paths:
            _observer.schedule(_handler, p, recursive=True)
        _observer.start()
        _current_paths = new_paths

    for p in added:
        threading.Thread(target=_initial_scan, args=(p,), daemon=True).start()

    print("Watchdog restarted:", new_paths, flush=True)


def _watch_path_poller(interval: int = 5):
    global _current_paths
    while True:
        try:
            paths = set(fetch_watch_paths())
            if paths != _current_paths:
                _restart_watchdog(paths)
        except Exception as e:
            print("Watch path fetch failed:", e, flush=True)
        time.sleep(interval)


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ensure_state_file()
    wait_for_server()

    # initial scan of already-configured paths
    threading.Thread(target=lambda: [
        threading.Thread(target=_initial_scan, args=(p,), daemon=True).start()
        for p in fetch_watch_paths()
    ], daemon=True).start()

    # poll for watch path changes
    threading.Thread(target=_watch_path_poller, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if _observer:
            _observer.stop()
            _observer.join()
