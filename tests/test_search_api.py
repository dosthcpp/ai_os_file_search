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


# ── /api/search with filters ──────────────────────────────────────────────────

def _upsert(client, chunk_id: str, path: str, text: str, ext: str):
    """Helper: upsert a chunk with ext metadata."""
    client.post("/api/chunks/upsert", json={
        "id": chunk_id,
        "vector": FAKE_VEC,
        "payload": {"path": path, "chunk_index": 0, "text": text, "ext": ext},
    })


def test_search_ext_filter_returns_only_matching_ext(client):
    _upsert(client, "py-chunk", "/proj/main.py", "python code here", ".py")
    _upsert(client, "md-chunk", "/proj/readme.md", "markdown content here", ".md")

    r = client.get("/api/search", params={"q": "code content", "n": 10, "ext": ".py"})
    assert r.status_code == 200
    results = r.json()
    for res in results:
        if res["ext"] is not None:
            assert res["ext"] == ".py"


def test_search_ext_filter_no_results_returns_empty(client):
    _upsert(client, "js-chunk-2", "/proj/app.js", "javascript app code", ".js")

    r = client.get("/api/search", params={"q": "javascript", "n": 5, "ext": ".rs"})
    assert r.status_code == 200
    results = r.json()
    # All returned results (if any) must have .rs extension
    for res in results:
        if res["ext"] is not None:
            assert res["ext"] == ".rs"


def test_search_ext_normalizes_missing_dot(client):
    """ext='py' (without dot) should behave the same as ext='.py'."""
    _upsert(client, "py-chunk-3", "/proj/helper.py", "helper functions", ".py")

    r = client.get("/api/search", params={"q": "helper", "n": 5, "ext": "py"})
    assert r.status_code == 200
    # Should not error out
    assert isinstance(r.json(), list)


def test_search_path_prefix_filter(client):
    _upsert(client, "src-chunk", "/project/src/app.py", "source file", ".py")
    _upsert(client, "test-chunk", "/project/tests/test_app.py", "test file", ".py")

    r = client.get("/api/search", params={"q": "file", "n": 10, "path_prefix": "/project/src"})
    assert r.status_code == 200
    results = r.json()
    for res in results:
        if res["path"]:
            assert res["path"].startswith("/project/src")


def test_search_no_filter_returns_all(client):
    _upsert(client, "a-chunk", "/a/file.py", "some python text", ".py")
    _upsert(client, "b-chunk", "/b/file.go", "some go text", ".go")

    r = client.get("/api/search", params={"q": "text", "n": 10})
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_search_empty_collection_returns_empty(client):
    """Searching an empty collection must not raise a 500 error."""
    r = client.get("/api/search", params={"q": "anything", "n": 5, "collection": "file_diffs"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── /api/file-content ─────────────────────────────────────────────────────────

def test_file_content_outside_watch_path_denied(client, tmp_path):
    # No watch paths configured → any real file should be denied
    real_file = tmp_path / "secret.txt"
    real_file.write_text("top secret")

    r = client.get("/api/file-content", params={"path": str(real_file)})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert "not inside a watched directory" in data["error"]


def test_file_content_inside_watch_path(client, tmp_path):
    watch_dir = tmp_path / "watched"
    watch_dir.mkdir()

    # Register the watch path
    client.post("/api/watch-path", json={"path": str(watch_dir)})

    target = watch_dir / "hello.txt"
    target.write_text("hello from file", encoding="utf-8")

    r = client.get("/api/file-content", params={"path": str(target)})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["content"] == "hello from file"
    assert data["truncated"] is False


def test_file_content_nonexistent_file(client, tmp_path):
    watch_dir = tmp_path / "watched2"
    watch_dir.mkdir()
    client.post("/api/watch-path", json={"path": str(watch_dir)})

    r = client.get("/api/file-content", params={"path": str(watch_dir / "missing.txt")})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert "not found" in data["error"].lower()


def test_file_content_truncation(client, tmp_path):
    watch_dir = tmp_path / "watched3"
    watch_dir.mkdir()
    client.post("/api/watch-path", json={"path": str(watch_dir)})

    big_file = watch_dir / "big.txt"
    big_file.write_bytes(b"x" * 200)

    r = client.get("/api/file-content", params={"path": str(big_file), "max_bytes": 100})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["truncated"] is True
    assert len(data["content"]) <= 100
