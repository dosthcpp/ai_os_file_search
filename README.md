# AI OS File Search

Semantic file search for your local machine.
Files are monitored in real time, chunked, embedded with **OpenAI**, stored in a local **ChromaDB** database, and made searchable through a **FastAPI** REST API with a **React** frontend.

---

## Architecture

```
webapp/          React + TypeScript UI (Vite)
apps/search_api/ FastAPI server — ChromaDB + OpenAI embeddings
packages/core/   Shared embedder (openai) and ChromaDB client
packages/file-indexer/  File watcher daemon (watchdog)
config/          settings.json — watch paths, server URL, file size limit
data/chroma/     Local ChromaDB persistent storage (created at runtime)
tests/           Pytest test suite (TDD)
```

---

## Prerequisites

- Python 3.9+
- Node.js 18+ / npm or yarn
- An **OpenAI API key** (`OPENAI_API_KEY` environment variable)

---

## Quick Start

### 1. Clone and set up Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows
```

### 2. Install Python dependencies

```bash
# API server + shared packages
pip install -r apps/search_api/requirements.txt
pip install -r packages/core/requirements.txt

# File indexer daemon
pip install -r packages/file-indexer/requirements.txt
```

### 3. Install frontend dependencies

```bash
cd webapp && npm install && cd ..
```

### 4. Set your OpenAI API key

```bash
export OPENAI_API_KEY="sk-..."
```

### 5. Start all services (via npm scripts)

```bash
npm install           # install concurrently
npm run dev           # starts API + indexer + webapp in parallel
```

Or start each service individually:

```bash
# API server (port 8000)
uvicorn apps.search_api.main:app --reload --port 8000

# File indexer daemon (in packages/file-indexer/)
cd packages/file-indexer && python main.py

# Frontend dev server
cd webapp && npm run dev
```

---

## Configuration

`config/settings.json` is auto-created on first run with defaults:

```json
{
  "watch_paths": [],
  "max_file_size_mb": 2,
  "server_url": "http://127.0.0.1:8000"
}
```

Use the **Watch Path Settings** panel in the UI (or `POST /api/watch-path`) to add directories to monitor.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Server health check |
| `GET` | `/api/watch-paths` | List configured watch paths |
| `POST` | `/api/watch-path` | Add a watch path `{"path": "/..."}` |
| `DELETE` | `/api/watch-path` | Remove a watch path |
| `GET` | `/api/search?q=...&n=5` | Semantic search (OpenAI embedding) |
| `POST` | `/api/chunks/upsert` | Index a text chunk with its vector |
| `POST` | `/api/delete` | Delete chunk IDs from the index |
| `POST` | `/api/diff` | Store a file diff |
| `GET` | `/api/diff?path=...` | Retrieve the latest diff for a file |
| `POST` | `/api/file-change` | Record a file add/modify/delete event |
| `GET` | `/api/changed-files` | List all tracked file change events |
| `GET` | `/api/changed-files/tree` | File-tree view of latest changes |
| `POST` | `/api/save-file-version` | Store a versioned snapshot |
| `GET` | `/api/files` | List the latest version of every tracked file |
| `GET` | `/api/files/versions?path=...` | Version history for a file |
| `GET` | `/api/files/version/diff?path=...&version=N` | Diff for a specific version |
| `WS` | `/ws/file-tree` | Live file-tree updates via WebSocket |

---

## Embedding Details

| Setting | Value |
|---------|-------|
| Provider | OpenAI |
| Model | `text-embedding-3-small` |
| Dimensions | 1536 |
| Distance metric | Cosine similarity |

To switch models, change `EMBEDDING_MODEL` and `EMBEDDING_DIM` in `packages/core/embedder.py`.
**Note:** changing these constants requires wiping the existing ChromaDB data (`data/chroma/`) because stored vectors will have a different dimension.

---

## Running Tests

```bash
pip install -r tests/requirements.txt
pytest tests/ -v
```

Test coverage:

| File | Tests |
|------|-------|
| `test_chunker.py` | Text chunking logic |
| `test_text_extractor.py` | Multi-format text extraction |
| `test_utils.py` | State management, diff, UUID helpers |
| `test_embedder.py` | OpenAI embedding module (mocked) |
| `test_search_api.py` | FastAPI endpoint integration (mocked) |

---

## Docker (optional ChromaDB server)

A `docker-compose.yml` is provided if you prefer a standalone ChromaDB server instead of the embedded client:

```bash
docker compose up -d chroma
```

Update `apps/search_api/main.py` to use `chromadb.HttpClient` pointing at `localhost:8100`.
