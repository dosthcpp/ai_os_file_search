from __future__ import annotations

import difflib
import json
import os
import uuid

STATE_FILE = ".local_index_state.json"
NAMESPACE = uuid.UUID("20b57fa4-ec8b-4ce0-b0d5-7b56a25385db")

TEMP_PREFIXES = ("~",)
TEMP_EXTENSIONS = (".tmp",)


def is_temp_file(path: str) -> bool:
    name = os.path.basename(path).lower()
    return name.startswith(TEMP_PREFIXES) or name.endswith(TEMP_EXTENSIONS)


def ensure_state_file():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            json.dump({}, f)


def chunk_id_to_uuid(chunk_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, chunk_id))


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        save_state({})
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        save_state({})
        return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def update_state(path: str, file_hash: str, chunk_ids: list[str], stat, text: str, version: int = None):
    state = load_state()
    entry = state.get(path, {})
    entry.update({
        "hash": file_hash,
        "chunks": chunk_ids,
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "text": text,
    })
    if version is not None:
        entry["version"] = version
    state[path] = entry
    save_state(state)


def compute_diff(old: str, new: str) -> list[str]:
    return list(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        lineterm="", fromfile="before", tofile="after"
    ))
