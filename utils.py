import os
import json
from client import delete_chunks
import uuid
import difflib

STATE_FILE = ".local_index_state.json"

NAMESPACE = uuid.UUID("20b57fa4-ec8b-4ce0-b0d5-7b56a25385db")
# ← 아무 UUID 하나 고정으로 써도 됨 (프로젝트 고유)

TEMP_PREFIXES = ("~",)
TEMP_EXTENSIONS = (".tmp",)

def chunk_id_to_uuid(chunk_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, chunk_id))


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def update_state(
    path: str,
    file_hash: str,
    chunk_ids: list[str],
    stat,
    text: str           # 🔥 추가
):
    state = load_state()

    state[path] = {
        "hash": file_hash,
        "chunks": chunk_ids,
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "text": text     # 🔥 이전 전체 텍스트 저장
    }

    save_state(state)

def handle_deleted_files(prev_state, new_state):
    deleted_paths = set(prev_state.keys()) - set(new_state.keys())

    for path in deleted_paths:
        chunks = prev_state[path].get("chunks", [])
        if chunks:
            delete_chunks(chunks)
            print(f"Deleted: {path}")

def compute_diff(old: str, new: str):
    old_lines = old.splitlines()
    new_lines = new.splitlines()

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        lineterm="",
        fromfile="before",
        tofile="after"
    )

    return list(diff)

def is_temp_file(path: str) -> bool:
    name = os.path.basename(path).lower()
    return name.startswith(TEMP_PREFIXES) or name.endswith(TEMP_EXTENSIONS)