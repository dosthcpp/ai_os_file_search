# AI OS

A local file-monitoring and semantic-search system.
Watch directories are tracked in real time; file contents are chunked, embedded via OpenAI, and stored in a local ChromaDB instance.
A React web UI lets you browse the file tree, inspect version history, view diffs, and run natural-language searches.

---

## Architecture

```
[Watched directories]
        │  watchdog events
        ▼
  indexer/main.py          ← Python 3.11+, watchdog
  (chunk → embed → upload)
        │  HTTP (REST)
        ▼
  apps/search_api/main.py  ← FastAPI + ChromaDB (local, persistent)
        │  HTTP / WebSocket
        ▼
  webapp/                  ← React 19 + TypeScript + Antd
```

---

## Requirements

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| OpenAI API key | `OPENAI_API_KEY` env var |

---

## Setup

```bash
# 1. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# 2. Install Python dependencies
pip install -r apps/search_api/requirements.txt
pip install -r indexer/requirements.txt

# 3. Install JS dependencies
cd webapp && yarn && cd ..

# 4. Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# 5. Start everything
npm run dev
```

`npm run dev` concurrently starts:
- **Search API** — `uvicorn apps.search_api.main:app --reload --port 8000`
- **Indexer** — `python indexer/main.py`
- **Webapp** — Vite dev server (default port 5173)

---

## Configuration

`config/settings.json` is written automatically by the server.

```json
{
  "watch_paths": [],
  "max_file_size_mb": 2,
  "server_url": "http://127.0.0.1:8000"
}
```

Add watch directories via the web UI or `POST /api/watch-path`.

---

## Embedding model

| | Before | After (current) |
|--|--------|-----------------|
| Provider | sentence-transformers (local) | OpenAI API |
| Model | all-MiniLM-L6-v2 | text-embedding-3-small |
| Dimension | 384 | 1536 |

> **Note:** switching models requires clearing the ChromaDB data directory (`data/chroma/`) because the vector dimensions are different.

---

## Key API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server status + model info |
| GET | `/api/watch-paths` | List watch paths |
| POST | `/api/watch-path` | Add a watch path |
| DELETE | `/api/watch-path` | Remove a watch path |
| GET | `/api/search?q=...` | Semantic search |
| GET | `/api/changed-files/tree` | File tree JSON |
| GET | `/api/files/versions?path=...` | Version history |
| GET | `/api/files/version/diff?path=...&version=N` | Version diff |
| WS | `/ws/file-tree` | Real-time tree updates |

---

## Data storage

| What | Where |
|------|-------|
| ChromaDB vectors | `data/chroma/` |
| Settings | `config/settings.json` |
| Indexer state | `.local_index_state.json` (project root) |
