"""
Tests for packages/file-indexer/utils.py
"""
import json
import os
import pytest
from utils import (
    chunk_id_to_uuid,
    compute_diff,
    ensure_state_file,
    is_temp_file,
    load_state,
    save_state,
    update_state,
)

# ── is_temp_file ─────────────────────────────────────────────────────────────

def test_temp_file_tilde_prefix():
    assert is_temp_file("~lockfile") is True


def test_temp_file_tmp_extension():
    assert is_temp_file("document.tmp") is True


def test_temp_file_tmp_extension_uppercase():
    assert is_temp_file("document.TMP") is True


def test_normal_file_not_temp():
    assert is_temp_file("myfile.txt") is False


def test_python_file_not_temp():
    assert is_temp_file("main.py") is False


def test_temp_prefix_in_path():
    assert is_temp_file("/some/dir/~lockfile") is True


# ── chunk_id_to_uuid ─────────────────────────────────────────────────────────

def test_uuid_format():
    uid = chunk_id_to_uuid("abc123_0")
    assert len(uid) == 36
    parts = uid.split("-")
    assert len(parts) == 5


def test_uuid_deterministic():
    assert chunk_id_to_uuid("same_input") == chunk_id_to_uuid("same_input")


def test_uuid_different_inputs_produce_different_uuids():
    assert chunk_id_to_uuid("input_a") != chunk_id_to_uuid("input_b")


# ── compute_diff ─────────────────────────────────────────────────────────────

def test_diff_identical_returns_empty():
    result = compute_diff("same\ntext\n", "same\ntext\n")
    assert result == []


def test_diff_detects_added_line():
    diff = compute_diff("line1\n", "line1\nline2\n")
    assert any("+line2" in l for l in diff)


def test_diff_detects_removed_line():
    diff = compute_diff("line1\nline2\n", "line1\n")
    assert any("-line2" in l for l in diff)


def test_diff_detects_modified_line():
    diff = compute_diff("old text\n", "new text\n")
    assert any("-old text" in l for l in diff)
    assert any("+new text" in l for l in diff)


def test_diff_both_empty():
    assert compute_diff("", "") == []


# ── load_state / save_state ───────────────────────────────────────────────────

def test_save_and_load_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = {"file.txt": {"hash": "abc", "version": 1}}
    save_state(state)
    loaded = load_state()
    assert loaded == state


def test_load_state_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = load_state()
    assert result == {}


def test_load_state_corrupt_json_returns_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".local_index_state.json").write_text("NOT JSON")
    result = load_state()
    assert result == {}


# ── ensure_state_file ─────────────────────────────────────────────────────────

def test_ensure_state_file_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ensure_state_file()
    state_path = tmp_path / ".local_index_state.json"
    assert state_path.exists()
    data = json.loads(state_path.read_text())
    assert data == {}


def test_ensure_state_file_does_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state_path = tmp_path / ".local_index_state.json"
    state_path.write_text('{"key": "value"}')
    ensure_state_file()
    data = json.loads(state_path.read_text())
    assert data == {"key": "value"}


# ── update_state ──────────────────────────────────────────────────────────────

def test_update_state_creates_entry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class FakeStat:
        st_mtime = 1000.0
        st_size = 512

    update_state("/path/to/file.txt", "hash123", ["chunk-1"], FakeStat(), "content", version=1)
    state = load_state()
    assert "/path/to/file.txt" in state
    entry = state["/path/to/file.txt"]
    assert entry["hash"] == "hash123"
    assert entry["chunks"] == ["chunk-1"]
    assert entry["version"] == 1


def test_update_state_updates_existing_entry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_state({"/path/file.txt": {"hash": "old", "version": 1}})

    class FakeStat:
        st_mtime = 2000.0
        st_size = 1024

    update_state("/path/file.txt", "new_hash", ["c1", "c2"], FakeStat(), "new content", version=2)
    state = load_state()
    assert state["/path/file.txt"]["hash"] == "new_hash"
    assert state["/path/file.txt"]["version"] == 2
