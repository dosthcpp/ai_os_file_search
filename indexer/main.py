"""
Indexer — watches configured directories and sends file content to the search API.

Flow:
  1. On startup: scan all watch paths to index existing files.
  2. Watchdog thread: handle real-time create/modify/delete events.
  3. Path-watcher thread: poll the API every 5 s for watch-path changes;
     restart the watchdog observer whenever the set of paths changes.

Requires OPENAI_API_KEY to be set in the environment (used by embedder.py).
"""
import hashlib
import json
import os
import time

BASE_PATH = os.getcwd()

with open(f"{BASE_PATH}/indexer/config.json") as f:
    config = json.load(f)

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from chunker import chunk_text
from client import upload_chunk, delete_chunks, upload_file, send_diff, send_file_change, wait_for_server, \
    fetch_watch_paths, save_file_change
from embedder import get_embedding
from text_extractor import extract_text
from utils import load_state, save_state, update_state, handle_deleted_files, chunk_id_to_uuid, compute_diff, \
    is_temp_file, ensure_state_file

import threading

# Grace period before finalising a delete (helps with macOS atomic saves)
DELETE_DELAY = 1.0  # seconds
pending_deletes: dict[str, threading.Timer] = {}

def cancel_pending_delete(path: str):
    """Cancel a scheduled delete if the file reappeared (e.g. rename/atomic write)."""
    t = pending_deletes.pop(path, None)
    if t:
        t.cancel()

MAX_SIZE = config["max_file_size_mb"] * 1024 * 1024

def file_hash(path: str) -> str:
    """Return the MD5 hex digest of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

# Tracks files currently being indexed to prevent duplicate work
INFLIGHT: set[str] = set()
INFLIGHT_LOCK = threading.Lock()


def summarize_diff(diff: str, max_len: int = 200) -> str:
    """Build a short human-readable summary of a unified diff."""
    if not diff:
        return ""
    lines = diff.splitlines()
    added = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
    summary = f"Added {added} lines, removed {removed} lines"
    preview = " ".join(lines[:5])
    return f"{summary}. Changes: {preview[:max_len]}"


def save_file_version(
    path: str,
    version: int,
    diff: list[str],
    summary: str,
    _hash: str,
    change_type: str,
):
    """Persist a file version record to the API, including an embedding of the summary."""
    save_file_change(path, version, diff, summary, get_embedding(summary), _hash, change_type)


def record_delete_version(path: str, prev_state: dict):
    """Record a deletion event as a new version."""
    save_file_version(
        path=path,
        version=prev_state["version"] + 1,
        diff="(file deleted)",
        summary="File deleted",
        _hash=prev_state["hash"],
        change_type="deleted",
    )


def index_file(path: str, from_scan: bool = False):
    """Extract, chunk, embed, and upload a single file to the search API."""
    if is_temp_file(path):
        return
    if not os.path.exists(path):
        return

    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return

    # Skip files that exceed the configured size limit
    if stat.st_size > MAX_SIZE:
        return

    # During initial scan we skip the SCANNING_PATHS guard
    if not from_scan:
        for scanning_path in SCANNING_PATHS:
            if path.startswith(scanning_path):
                return

    # Prevent concurrent indexing of the same file
    with INFLIGHT_LOCK:
        if path in INFLIGHT:
            return
        INFLIGHT.add(path)

    try:
        current_hash = file_hash(path)
        prev_state = load_state().get(path)

        is_new = prev_state is None  # file not seen before
        is_modified = prev_state is not None and prev_state["hash"] != current_hash

        old_text = prev_state.get("text") if prev_state else ""
        text = extract_text(path)

        if not text:
            return

        chunks = chunk_text(text)
        chunk_ids = []

        for i, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            logical_id = f"{file_hash(path)}_{i}"
            chunk_id = chunk_id_to_uuid(logical_id)
            chunk_ids.append(chunk_id)

            # Upload chunk with embedding to the search API
            upload_chunk(
                chunk_id=chunk_id,
                vector=emb,
                payload={
                    "path": path,
                    "chunk_index": i,
                    "text": chunk[:300],
                },
            )

        diff = compute_diff(old_text, text)
        prev_version = prev_state.get("version", 0) if prev_state else 0
        new_version = prev_version + 1

        update_state(
            path=path,
            file_hash=current_hash,
            chunk_ids=chunk_ids,
            stat=stat,
            text=text,
            version=new_version,
        )

        if is_new:
            send_file_change(path, "added")
            save_file_version(
                path=path,
                version=new_version,
                diff=diff,
                summary="Initial version",
                _hash=current_hash,
                change_type="added",
            )
        elif is_modified:
            send_file_change(path, "modified")
            if diff:
                summary = summarize_diff(text)
                save_file_version(
                    path=path,
                    version=new_version,
                    diff=diff,
                    summary=summary,
                    _hash=current_hash,
                    change_type="modified",
                )
                send_diff(path=path, old_text=old_text or "", new_text=text)

    finally:
        with INFLIGHT_LOCK:
            INFLIGHT.discard(path)


def handle_file_delete(path: str):
    """Remove a deleted file's chunks from the API and clean up local state."""
    state = load_state()
    info = state.get(path)

    # Ignore files that were never indexed
    if not info:
        return

    chunk_ids = info.get("chunks", [])
    if chunk_ids:
        delete_chunks(chunk_ids)
        print(f"[DEL] Removed chunks for: {path}")

    state.pop(path, None)
    save_state(state)
    send_file_change(path, "deleted")


def finalize_delete(path: str):
    """Called after DELETE_DELAY; skipped if the file reappeared in the meantime."""
    if os.path.exists(path):
        return  # file came back (atomic write or rename)
    handle_file_delete(path)
    pending_deletes.pop(path, None)


def delayed_index(path: str, delay: float = 0.3):
    """Schedule index_file after a short delay to debounce rapid writes."""
    def _run():
        if os.path.exists(path):
            index_file(path)
    threading.Timer(delay, _run).start()


class FileChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or is_temp_file(event.src_path):
            return
        print("[EVT created]", event.src_path, flush=True)
        cancel_pending_delete(event.src_path)
        delayed_index(event.src_path)

    def on_modified(self, event):
        if event.is_directory or is_temp_file(event.src_path):
            return
        print("[EVT modified]", event.src_path, flush=True)
        cancel_pending_delete(event.src_path)
        delayed_index(event.src_path)

    def on_deleted(self, event):
        """Use a grace-period timer to avoid false deletes on macOS atomic writes."""
        if event.is_directory:
            return
        path = event.src_path
        timer = threading.Timer(DELETE_DELAY, lambda: finalize_delete(path))
        pending_deletes[path] = timer
        timer.start()


observer: Observer | None = None
current_paths: set[str] = set()
observer_lock = threading.Lock()
handler = FileChangeHandler()
SCANNING_PATHS: set[str] = set()
SCANNING_LOCK = threading.Lock()


def initial_scan_path(path: str):
    """Index all existing files under *path* and mark any missing ones as deleted."""
    print("[SCAN] starting:", path, flush=True)

    # Snapshot state before scan to detect deletions
    state_before = load_state()
    prev_state = {k: v for k, v in state_before.items() if k.startswith(path)}

    with SCANNING_LOCK:
        SCANNING_PATHS.add(path)
    try:
        scan_directory(path)
    finally:
        with SCANNING_LOCK:
            SCANNING_PATHS.discard(path)

    # Compare pre/post snapshots and handle any files that disappeared
    state_after = load_state()
    handle_deleted_files(prev_state, state_after)
    save_state(state_after)


def restart_watchdog(new_paths: set[str]):
    """Stop the current observer and start a new one watching *new_paths*."""
    global observer, current_paths
    added = new_paths - current_paths

    with observer_lock:
        if observer:
            observer.stop()
            observer.join()

        observer = Observer()
        for path in new_paths:
            observer.schedule(handler, path, recursive=True)
        observer.start()
        current_paths = new_paths

    # Scan newly added paths in background threads
    for p in added:
        threading.Thread(target=initial_scan_path, args=(p,), daemon=True).start()

    print("[WATCH] observer restarted for paths:", new_paths, flush=True)


def watch_path_watcher(interval: int = 5):
    """Periodically fetch the watch-path list from the API and restart the observer if changed."""
    global current_paths
    while True:
        try:
            paths = set(fetch_watch_paths())
            if paths != current_paths:
                restart_watchdog(paths)
        except Exception as e:
            print("[WARN] watch path fetch failed:", e, flush=True)
        time.sleep(interval)


def scan_directory(base: str):
    """Walk *base* recursively and index every file found."""
    for root, _, files in os.walk(base):
        for file in files:
            full_path = os.path.join(root, file)
            index_file(full_path, from_scan=True)


def scan():
    """Initial scan of all currently configured watch paths."""
    paths = fetch_watch_paths()
    for path in paths:
        initial_scan_path(path)


if __name__ == "__main__":
    ensure_state_file()
    wait_for_server()

    # Initial scan of existing files
    threading.Thread(target=scan, daemon=True).start()

    # Background thread that polls the API for watch-path changes
    threading.Thread(target=watch_path_watcher, daemon=True).start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if observer:
            observer.stop()
            observer.join()
