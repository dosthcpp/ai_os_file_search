"""
AI OS — File Indexer

Daemon that watches configured directories for file changes and sends
embeddings + metadata to the Search API server.

Flow:
  1. Wait for the API server to be ready.
  2. Poll /api/watch-paths every 5 s; restart watchdog whenever the list changes.
  3. On file create/modify: extract text → chunk → embed → upload chunks.
  4. On file delete: remove chunks from the index and record a deletion version.
  5. On startup: scan all configured paths to catch any changes that occurred
     while the indexer was offline.
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ── add packages/core to sys.path so shared modules are importable ────────────
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "packages" / "core"))

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from chunker import chunk_text
from clip_embedder import clip_available, get_image_embedding  # noqa: E402 (core)
from ocr_extractor import extract_text_from_image, is_image
from client import (
    delete_chunks,
    delete_image_embedding,
    fetch_watch_paths,
    save_file_version,
    send_diff,
    send_file_change,
    upload_chunk,
    upload_image_embedding,
    wait_for_server,
)
from embedder import get_embedding  # noqa: E402 (core)
from text_extractor import extract_text
from secret_scanner import SecretScanner
from sec_ai_analyzer import SecAIAnalyzer
from utils import (
    chunk_id_to_uuid,
    compute_diff,
    ensure_state_file,
    is_temp_file,
    load_state,
    save_state,
    update_state,
)

# ── config ────────────────────────────────────────────────────────────────────
SETTINGS_FILE = ROOT_DIR / "config" / "settings.json"


def max_file_size() -> int:
    """Return the maximum indexable file size in bytes (from settings.json)."""
    try:
        s = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return s.get("max_file_size_mb", 2) * 1024 * 1024
    except Exception:
        return 2 * 1024 * 1024


# ── delete debounce ───────────────────────────────────────────────────────────
DELETE_DELAY = 1.0  # seconds to wait before confirming a delete event
_pending_deletes: dict[str, threading.Timer] = {}


def _cancel_pending_delete(path: str):
    """Cancel a scheduled delete if the file was recreated/modified."""
    t = _pending_deletes.pop(path, None)
    if t:
        t.cancel()


# ── in-flight guard (prevents double-indexing the same file) ──────────────────
INFLIGHT: set[str] = set()
INFLIGHT_LOCK = threading.Lock()

# ── scanning guard (suppresses watchdog events during initial scan) ───────────
SCANNING_PATHS: set[str] = set()
SCANNING_LOCK = threading.Lock()


# ── helpers ───────────────────────────────────────────────────────────────────

def _summarize_diff(diff: list[str], max_len: int = 200) -> str:
    """Return a human-readable summary of a unified diff."""
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    preview = " ".join(diff[:5])
    return f"Added {added} lines, removed {removed} lines. Changes: {preview[:max_len]}"


def _file_hash(path: str) -> str:
    """Return the MD5 hex digest of a file's contents."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ── core indexing logic ───────────────────────────────────────────────────────

def index_file(path: str, from_scan: bool = False):
    """
    Index a single file: extract text, generate embeddings, upload chunks.

    Skips the file if:
      - it is a temp file
      - it no longer exists
      - it exceeds the size limit
      - it is being indexed by another thread
      - it has not changed since last index (same hash)
      - a directory scan is currently running for its parent path (unless
        this call is itself part of that scan, i.e. from_scan=True)
    """
    if is_temp_file(path) or not os.path.exists(path):
        return

    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return

    if stat.st_size > max_file_size():
        return

    # Suppress watchdog events fired during an ongoing initial scan
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
        prev_version = prev_state.get("version", 0) if prev_state else 0

        # Phase 3: OCR text extraction for image files
        if is_image(path):
            text = extract_text_from_image(path)
        else:
            text = extract_text(path)

        # Phase 3: CLIP visual embedding (stored in the separate images_clip collection)
        if is_image(path) and clip_available():
            image_emb = get_image_embedding(path)
            if image_emb:
                upload_image_embedding(path=path, image_vector=image_emb, file_hash=current_hash)

        if not text:
            # Image with no OCR text (or unsupported file type): persist the hash
            # so we skip re-processing on the next scan without losing CLIP data.
            update_state(path=path, file_hash=current_hash, chunk_ids=[],
                         stat=stat, text="", version=prev_version + 1)
            send_file_change(path, "added" if is_new else "modified")
            return

        # Phase 4: Secret Scanning (Security Audit)
        security_meta = SecretScanner.get_summary_metadata(text)
        
        # Phase 5: SecAI & Voice Phishing Analysis
        sec_ai_meta = SecAIAnalyzer.get_summary_metadata(text)
        security_meta.update(sec_ai_meta)

        chunks = chunk_text(text)
        chunk_ids = []

        ext = os.path.splitext(path)[1].lower()
        for i, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            chunk_id = chunk_id_to_uuid(f"{current_hash}_{i}")
            chunk_ids.append(chunk_id)
            
            # Combine basic payload with security metadata
            payload = {"path": path, "chunk_index": i, "text": chunk[:300], "ext": ext}
            payload.update(security_meta)
            
            upload_chunk(
                chunk_id=chunk_id,
                vector=emb,
                payload=payload,
            )

        diff = compute_diff(old_text, text)
        new_version = prev_version + 1

        update_state(path=path, file_hash=current_hash, chunk_ids=chunk_ids,
                     stat=stat, text=text, version=new_version)

        if is_new:
            send_file_change(path, "added")
            save_file_version(
                path=path, version=new_version, diff=diff,
                summary="Initial version",
                vector=get_embedding("Initial version"),
                file_hash=current_hash, change_type="added",
            )

        elif is_modified and diff:
            summary = _summarize_diff(diff)
            send_file_change(path, "modified")
            save_file_version(
                path=path, version=new_version, diff=diff,
                summary=summary,
                vector=get_embedding(summary),
                file_hash=current_hash, change_type="modified",
            )
            send_diff(path=path, old_text=old_text, new_text=text)

    finally:
        with INFLIGHT_LOCK:
            INFLIGHT.discard(path)


def _handle_file_delete(path: str):
    """Remove a deleted file's chunks from the index and record a deletion version."""
    state = load_state()
    info = state.get(path)
    if not info:
        return

    chunk_ids = info.get("chunks", [])
    if chunk_ids:
        delete_chunks(chunk_ids)

    # Phase 3: remove CLIP embedding for image files
    if is_image(path):
        delete_image_embedding(path)

    save_file_version(
        path=path,
        version=info.get("version", 0) + 1,
        diff=["(file deleted)"],
        summary="File deleted",
        vector=get_embedding("File deleted"),
        file_hash=info.get("hash", ""),
        change_type="deleted",
    )

    state.pop(path, None)
    save_state(state)
    send_file_change(path, "deleted")
    print(f"[DEL] {path}", flush=True)


def _finalize_delete(path: str):
    """Called after DELETE_DELAY; only proceeds if the file truly no longer exists."""
    if os.path.exists(path):
        return
    _handle_file_delete(path)
    _pending_deletes.pop(path, None)


def _delayed_index(path: str, delay: float = 0.3):
    """Index a file after a short delay to let write operations complete."""
    def _run():
        if os.path.exists(path):
            index_file(path)
    threading.Timer(delay, _run).start()


# ── watchdog event handler ────────────────────────────────────────────────────

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
        # Debounce: wait DELETE_DELAY before treating this as a real delete
        timer = threading.Timer(DELETE_DELAY, lambda: _finalize_delete(path))
        _pending_deletes[path] = timer
        timer.start()


# ── watchdog lifecycle ────────────────────────────────────────────────────────

_observer: Observer | None = None
_current_paths: set[str] = set()
_observer_lock = threading.Lock()
_handler = FileChangeHandler()


def _initial_scan(path: str):
    """
    Walk *path* and index any new or changed files.
    After the scan, detect files that existed in the local state but are
    no longer on disk (deleted while the indexer was offline).
    """
    print("[SCAN] Starting:", path, flush=True)
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
    deleted = set(state_before.keys()) - set(state_after.keys())
    for p in deleted:
        _handle_file_delete(p)

    print("[SCAN] Done:", path, flush=True)


def _restart_watchdog(new_paths: set[str]):
    """Stop any running observer and start a fresh one for *new_paths*."""
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

    # Run initial scans for newly added paths in background threads
    for p in added:
        threading.Thread(target=_initial_scan, args=(p,), daemon=True).start()

    print("[WATCHDOG] Restarted for paths:", new_paths, flush=True)


def _watch_path_poller(interval: int = 5):
    """Poll the server for the current watch-path list and restart if changed."""
    global _current_paths
    while True:
        try:
            paths = set(fetch_watch_paths())
            if paths != _current_paths:
                _restart_watchdog(paths)
        except Exception as e:
            print("[POLL] Watch-path fetch failed:", e, flush=True)
        time.sleep(interval)


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ensure_state_file()
    wait_for_server()

    # Kick off initial scans for already-configured paths
    threading.Thread(target=lambda: [
        threading.Thread(target=_initial_scan, args=(p,), daemon=True).start()
        for p in fetch_watch_paths()
    ], daemon=True).start()

    # Continuously poll for watch-path changes
    threading.Thread(target=_watch_path_poller, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if _observer:
            _observer.stop()
            _observer.join()
