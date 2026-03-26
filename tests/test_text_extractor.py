"""
Tests for packages/file-indexer/text_extractor.py
"""
import os
import tempfile
import pytest
from text_extractor import extract_text


def _write_tmp(suffix: str, content: str) -> str:
    """Write content to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_extract_txt():
    path = _write_tmp(".txt", "hello world")
    try:
        result = extract_text(path)
        assert result == "hello world"
    finally:
        os.unlink(path)


def test_extract_md():
    path = _write_tmp(".md", "# Title\n\nSome content here.")
    try:
        result = extract_text(path)
        assert "Title" in result
        assert "content" in result
    finally:
        os.unlink(path)


def test_extract_log():
    path = _write_tmp(".log", "2024-01-01 INFO Starting server")
    try:
        result = extract_text(path)
        assert "INFO" in result
    finally:
        os.unlink(path)


def test_extract_py_includes_function_defs():
    code = "def foo():\n    pass\n\ndef bar(x, y):\n    return x + y\n"
    path = _write_tmp(".py", code)
    try:
        result = extract_text(path)
        assert "def foo():" in result
        assert "def bar(x, y):" in result
    finally:
        os.unlink(path)


def test_extract_py_includes_first_lines():
    lines = [f"line{i}" for i in range(60)]
    path = _write_tmp(".py", "\n".join(lines))
    try:
        result = extract_text(path)
        # First 50 lines must be present
        assert "line0" in result
        assert "line49" in result
    finally:
        os.unlink(path)


def test_extract_js():
    code = "function greet(name) { return 'Hello ' + name; }\n"
    path = _write_tmp(".js", code)
    try:
        result = extract_text(path)
        assert "function greet" in result
    finally:
        os.unlink(path)


def test_extract_unsupported_extension_returns_none():
    path = _write_tmp(".xyz", "some data")
    try:
        result = extract_text(path)
        assert result is None
    finally:
        os.unlink(path)


def test_extract_nonexistent_file_returns_none():
    result = extract_text("/nonexistent/path/to/file.txt")
    assert result is None


def test_extract_empty_txt():
    path = _write_tmp(".txt", "")
    try:
        result = extract_text(path)
        assert result == ""
    finally:
        os.unlink(path)
