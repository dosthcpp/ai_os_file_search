"""
Integration tests for apps/search_api/main.py FastAPI endpoints.

The OpenAI embedder and ChromaDB are mocked so tests run without external
services or API keys.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

# ── fixtures ──────────────────────────────────────────────────────────────────

FAKE_DIM = 1536
FAKE_VEC = [0.1] * FAKE_DIM


@pytest.fixture()
def mock_embed(monkeypatch):
    """Patch _embed in the search_api main module to return a fixed vector."""
    import main as api
    monkeypatch.setattr(api, "_embed", lambda text: FAKE_VEC)
    return FAKE_VEC


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """
    Create a TestClient with:
      - isolated ChromaDB in a temp directory
      - settings file pointing at the temp config
      - _embed replaced with a no-op
    """
    from fastapi.testclient import TestClient
    import main as api

    # Redirect ChromaDB storage to a temp path
    monkeypatch.setattr(api, "CHROMA_PATH", str(tmp_path / "chroma"))

    # Redirect settings file to a temp location
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"watch_paths": [], "max_file_size_mb": 2,
                                          "server_url": "http://127.0.0.1:8000"}))
    monkeypatch.setattr(api, "SETTINGS_FILE", settings_path)

    # Reset the ChromaDB singleton so it uses the patched path
    monkeypatch.setattr(api, "_chroma", None)

    # Replace embedding with a fixed vector
    monkeypatch.setattr(api, "_embed", lambda text: FAKE_VEC)

    with TestClient(api.app) as c:
        yield c


# ── /api/health ───────────────────────────────────────────────────────────────

def test_health_returns_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


# ── /api/watch-paths ─────────────────────────────────────────────────────────

def test_get_watch_paths_initially_empty(client):
    r = client.get("/api/watch-paths")
    assert r.status_code == 200
    assert r.json() == []


def test_add_watch_path_nonexistent_dir_fails(client):
    r = client.post("/api/watch-path", json={"path": "/nonexistent/dir/xyz"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False


def test_add_and_remove_watch_path(client, tmp_path):
    watch_dir = str(tmp_path / "watched")
    (tmp_path / "watched").mkdir()

    # Add
    r = client.post("/api/watch-path", json={"path": watch_dir})
    assert r.json()["ok"] is True

    r = client.get("/api/watch-paths")
    assert watch_dir in r.json()

    # Remove
    r = client.request("DELETE", "/api/watch-path", json={"path": watch_dir})
    assert r.json()["ok"] is True

    r = client.get("/api/watch-paths")
    assert watch_dir not in r.json()


# ── /api/chunks/upsert & /api/search ─────────────────────────────────────────

def test_upsert_chunk_and_search(client):
    # Upsert a chunk
    payload = {
        "id": "test-chunk-001",
        "vector": FAKE_VEC,
        "payload": {"path": "/tmp/test.txt", "chunk_index": 0, "text": "the quick brown fox"},
    }
    r = client.post("/api/chunks/upsert", json=payload)
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Search for it
    r = client.get("/api/search", params={"q": "fox", "n": 5})
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
    assert len(results) >= 1
    assert results[0]["path"] == "/tmp/test.txt"


def test_delete_chunks(client):
    # First upsert
    client.post("/api/chunks/upsert", json={
        "id": "to-delete-001",
        "vector": FAKE_VEC,
        "payload": {"path": "/tmp/delete_me.txt", "text": "delete test"},
    })

    # Then delete
    r = client.post("/api/delete", json=["to-delete-001"])
    assert r.status_code == 200
    assert r.json()["deleted"] == 1


# ── /api/diff ─────────────────────────────────────────────────────────────────

def test_save_and_get_diff(client):
    r = client.post("/api/diff", json={
        "path": "/tmp/myfile.txt",
        "old_text": "version one",
        "new_text": "version two",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = client.get("/api/diff", params={"path": "/tmp/myfile.txt"})
    assert r.status_code == 200
    data = r.json()
    assert data["old_text"] == "version one"
    assert data["new_text"] == "version two"


def test_get_diff_nonexistent_path(client):
    r = client.get("/api/diff", params={"path": "/nonexistent.txt"})
    assert r.status_code == 200
    data = r.json()
    assert data["old_text"] == ""
    assert data["new_text"] == ""


# ── /api/file-change & /api/changed-files ────────────────────────────────────

def test_record_and_retrieve_file_change(client):
    import time
    r = client.post("/api/file-change", json={
        "path": "/home/user/docs/report.txt",
        "status": "added",
        "timestamp": time.time(),
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = client.get("/api/changed-files")
    assert r.status_code == 200
    paths = [m["path"] for m in r.json()]
    assert "/home/user/docs/report.txt" in paths


def test_changed_files_tree_returns_root(client):
    r = client.get("/api/changed-files/tree")
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "dir"


# ── /api/save-file-version & /api/files ──────────────────────────────────────

def test_save_and_list_file_versions(client):
    r = client.post("/api/save-file-version", json={
        "path": "/project/main.py",
        "version": 1,
        "diff": ["+line added"],
        "vector": FAKE_VEC,
        "summary": "Initial version",
        "hash": "abc123",
        "change_type": "added",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = client.get("/api/files")
    assert r.status_code == 200
    paths = [f["path"] for f in r.json()]
    assert "/project/main.py" in paths


def test_list_file_versions_for_path(client):
    for v in range(1, 4):
        client.post("/api/save-file-version", json={
            "path": "/project/utils.py",
            "version": v,
            "diff": [f"+v{v}"],
            "vector": FAKE_VEC,
            "summary": f"Version {v}",
            "hash": f"hash{v}",
            "change_type": "modified",
        })

    r = client.get("/api/files/versions", params={"path": "/project/utils.py"})
    assert r.status_code == 200
    versions = r.json()
    assert len(versions) == 3
    # Should be sorted descending
    assert versions[0]["version"] == 3


def test_get_version_diff(client):
    client.post("/api/save-file-version", json={
        "path": "/project/app.py",
        "version": 2,
        "diff": ["-old", "+new"],
        "vector": FAKE_VEC,
        "summary": "Added feature",
        "hash": "def456",
        "change_type": "modified",
    })

    r = client.get("/api/files/version/diff",
                   params={"path": "/project/app.py", "version": 2})
    assert r.status_code == 200
    data = r.json()
    assert "-old" in data["diff"]
    assert "+new" in data["diff"]
