from __future__ import annotations

import csv
import io
import json
import os

from PyPDF2 import PdfReader
from docx import Document

from ocr_extractor import extract_text_from_image, is_image

# Optional dependencies (graceful fallback if not installed)
try:
    import yaml as _yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

try:
    from bs4 import BeautifulSoup as _BS
    _BS_AVAILABLE = True
except ImportError:
    _BS_AVAILABLE = False

# ── extension sets ──────────────────────────────────────────────────────────
_PLAINTEXT_EXTS = {".txt", ".md", ".log", ".rst", ".ini", ".toml", ".cfg", ".env"}
_CODE_EXTS = {
    ".py", ".js", ".ts", ".java",
    ".go", ".rs", ".rb", ".cpp", ".c", ".h", ".cs",
    ".tsx", ".jsx", ".swift", ".kt", ".scala",
    ".sh", ".bash", ".zsh",
}


def extract_text(path: str) -> str | None:
    """Return extracted text for *path*, or None if unsupported / unreadable."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in _PLAINTEXT_EXTS:
            return open(path, "r", encoding="utf-8", errors="ignore").read()
        elif ext in _CODE_EXTS:
            return _extract_code(path)
        elif ext == ".pdf":
            return _extract_pdf(path)
        elif ext == ".docx":
            return _extract_docx(path)
        elif ext == ".json":
            return _extract_json(path)
        elif ext in (".yaml", ".yml"):
            return _extract_yaml(path)
        elif ext == ".csv":
            return _extract_csv(path)
        elif ext in (".html", ".htm"):
            return _extract_html(path)
        elif is_image(path):
            return extract_text_from_image(path)
        else:
            return None
    except Exception:
        return None


# ── format-specific extractors ──────────────────────────────────────────────

def _extract_code(path: str) -> str:
    """Return function/class signatures plus the first 50 lines of source code."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()
    lines = code.split("\n")
    # Collect definition lines (Python, JS/TS, Java, Go, Rust, Ruby, C#, etc.)
    defs = [
        l for l in lines
        if any(kw in l for kw in (
            "def ", "function ", "class ", "fn ", "func ",
            "public ", "private ", "protected ", "async ",
        ))
    ]
    return "\n".join(defs + lines[:50])


def _extract_pdf(path: str) -> str:
    reader = PdfReader(path)
    texts = [page.extract_text() for page in reader.pages]
    return "\n".join(t for t in texts if t)


def _extract_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_json(path: str) -> str:
    """Flatten a JSON file into readable key: value lines."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
    lines: list[str] = []
    _flatten(data, "", lines)
    return "\n".join(lines)


def _extract_yaml(path: str) -> str:
    """Flatten a YAML file into readable key: value lines (requires PyYAML)."""
    if not _YAML_AVAILABLE:
        # Fallback: return raw text
        return open(path, "r", encoding="utf-8", errors="ignore").read()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = _yaml.safe_load(f)
    if data is None:
        return ""
    lines: list[str] = []
    _flatten(data, "", lines)
    return "\n".join(lines)


def _extract_csv(path: str) -> str:
    """Return a readable tabular representation of a CSV file (max 500 rows)."""
    with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return ""

    headers = rows[0]
    lines = [", ".join(headers)]  # header row
    for row in rows[1:501]:  # cap at 500 data rows
        if len(row) == len(headers):
            lines.append(", ".join(f"{h}: {v}" for h, v in zip(headers, row)))
        else:
            lines.append(", ".join(row))
    return "\n".join(lines)


def _extract_html(path: str) -> str:
    """Strip HTML tags and return the visible text content."""
    raw = open(path, "r", encoding="utf-8", errors="ignore").read()
    if _BS_AVAILABLE:
        soup = _BS(raw, "html.parser")
        # Remove script and style elements
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    # Fallback: naive tag-stripping with a simple state machine
    out, in_tag = [], False
    for ch in raw:
        if ch == "<":
            in_tag = True
        elif ch == ">":
            in_tag = False
            out.append(" ")
        elif not in_tag:
            out.append(ch)
    return "".join(out).strip()


# ── helpers ──────────────────────────────────────────────────────────────────

def _flatten(obj: object, prefix: str, lines: list[str], depth: int = 0) -> None:
    """Recursively flatten dicts/lists into 'key: value' lines (max depth 6)."""
    if depth > 6:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            _flatten(v, key, lines, depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:20]):  # cap list expansion at 20 items
            _flatten(v, f"{prefix}[{i}]", lines, depth + 1)
    else:
        val = str(obj)
        if val:
            lines.append(f"{prefix}: {val}" if prefix else val)
