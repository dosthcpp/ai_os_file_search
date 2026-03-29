# AI OS File Search

A local file-monitoring and semantic-search system.
Watch directories are tracked in real time; file contents are chunked, embedded via OpenAI, and stored in a local ChromaDB instance.
A React web UI lets you browse the file tree, inspect version history, view diffs, and run natural-language searches.

---

## Architecture

```
[Watched directories]
        │  watchdog events
        ▼
  packages/file-indexer/main.py   ← Python 3.9+, watchdog
  (chunk → embed → upload)
        │  HTTP (REST)
        ▼
  apps/search_api/main.py         ← FastAPI + ChromaDB (local, persistent)
        │  HTTP / WebSocket
        ▼
  webapp/                         ← React 19 + TypeScript + Antd
```

---

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | 3.9 minimum, 3.11+ recommended |
| Node.js | 18+ | |
| OpenAI API key | `OPENAI_API_KEY` env var | |
| Tesseract OCR | any | Optional — enables OCR for images. `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Ubuntu) |

---

## Setup

```bash
# 1. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# 2. Install Python dependencies
pip install -r apps/search_api/requirements.txt
pip install -r packages/core/requirements.txt
pip install -r packages/file-indexer/requirements.txt

# 3. Install JS dependencies
cd webapp && npm install && cd ..

# 4. Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# 5. Start everything
npm install && npm run dev
```

`npm run dev` concurrently starts:
- **Search API** — `uvicorn apps.search_api.main:app --reload --port 8000`
- **Indexer** — `python packages/file-indexer/main.py`
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

## Features

### Phase 1
- **OpenAI embeddings** — `text-embedding-3-small` (1536-dim) for semantic similarity search
- **Real-time file watching** — watchdog daemon tracks add / modify / delete events
- **Version control tracking** — every file change stored with diff, hash, and version number
- **SearchBar** — natural-language search over indexed file chunks
- **WatchPath management** — add/remove directories to monitor from the UI
- **WebSocket file tree** — live-updating directory tree

### Phase 2
- **Extended file type support** — JSON, YAML/YML, CSV, HTML/HTM are now fully indexed.
  Code language support expanded to Go, Rust, Ruby, C/C++, C#, Swift, Kotlin, TypeScript/React (tsx/jsx), and shell scripts.
- **Overlapping chunks** — `chunk_text()` accepts an `overlap` parameter (default 50 words).
  Overlapping chunks preserve cross-boundary context and improve semantic recall at chunk edges.
- **Search filters** — `/api/search` accepts optional `ext` and `path_prefix` query parameters.
  The **SearchBar** exposes a collapsible filter panel for both options.
- **File content preview** — click any file to view its raw content inline.
  `/api/file-content` serves files (must be inside a watched directory for security).
- **Tabbed right panel** — *File Content* and *Version History* tabs on the right side.
- **Search history** — recent queries persisted to `localStorage` with autocomplete dropdown.

### Phase 3
- **OCR text extraction** — images (PNG, JPG, WebP, TIFF, etc.) are scanned using Tesseract OCR.
  Extracted text is indexed alongside regular documents, making images searchable via text keywords.
- **Multimodal search (CLIP)** — uses OpenAI CLIP (ViT-B/32) to generate visual embeddings.
- **Natural-language image search** — a new `/api/search/images` endpoint allows searching for images using descriptive text (e.g., "a photo of a cat") via the CLIP text tower.
- **Independent modules** — CLIP and OCR logic are encapsulated in standalone packages for easy scaling.

---

## Embedding model

| Model | Dimension | Purpose |
|-------|-----------|---------|
| `text-embedding-3-small` | 1536 | Text & Document search |
| `openai/clip-vit-base-patch32` | 512 | Image & Multimodal search |

> **Note:** switching models requires clearing `data/chroma/` because the vector dimensions differ.

---

## Supported File Types

| Category | Extensions |
|----------|-----------|
| Plain text | `.txt` `.md` `.log` `.rst` `.ini` `.toml` `.cfg` `.env` |
| Source code | `.py` `.js` `.ts` `.tsx` `.jsx` `.java` `.go` `.rs` `.rb` `.cpp` `.c` `.h` `.cs` `.swift` `.kt` `.scala` `.sh` `.bash` `.zsh` |
| Data | `.json` `.yaml` `.yml` `.csv` |
| Documents | `.pdf` `.docx` `.html` `.htm` |
| Images (OCR/CLIP) | `.png` `.jpg` `.jpeg` `.webp` `.tiff` `.bmp` `.gif` |

---

## Chunking

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_words` | 400 | Maximum words per chunk |
| `overlap` | 50 | Words repeated between adjacent chunks |

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server status |
| GET | `/api/watch-paths` | List watch paths |
| POST | `/api/watch-path` | Add a watch path |
| DELETE | `/api/watch-path` | Remove a watch path |
| GET | `/api/search?q=...&ext=.py&path_prefix=...` | Semantic search with optional filters |
| GET | `/api/file-content?path=...&max_bytes=100000` | Read raw file content |
| GET | `/api/changed-files/tree` | File tree JSON |
| GET | `/api/files/versions?path=...` | Version history |
| GET | `/api/files/version/diff?path=...&version=N` | Version diff |
| GET | `/api/search/images?q=...` | CLIP-based image search |
| POST | `/api/images/index` | Manual image index entry |
| WS | `/ws/file-tree` | Real-time tree updates |

---

## Running Tests

```bash
pip install -r tests/requirements.txt
pytest tests/ -v
```

| File | Coverage |
|------|----------|
| `test_chunker.py` | Word chunking + overlap logic |
| `test_text_extractor.py` | All supported file format parsers |
| `test_utils.py` | State management, diff, UUID helpers |
| `test_embedder.py` | OpenAI embedding module (mocked) |
| `test_search_api.py` | FastAPI endpoints including search filters and file content |
| `test_ocr_extractor.py` | OCR text extraction: `is_image()`, graceful fallback, mock OCR pipeline |
| `test_clip_embedder.py` | CLIP embedder: constants, graceful fallback, mock model/processor pipeline |

---

## Data storage

| What | Where |
|------|-------|
| ChromaDB vectors | `data/chroma/` |
| Settings | `config/settings.json` |
| Indexer state | `.local_index_state.json` (project root) |
