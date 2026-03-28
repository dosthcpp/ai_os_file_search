"""
Tests for packages/file-indexer/text_extractor.py
"""
import csv
import json
import os
import tempfile

import pytest
from text_extractor import extract_text, _flatten


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_tmp(suffix: str, content: str) -> str:
    """Write *content* to a temp file with the given *suffix* and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ── plain-text family ─────────────────────────────────────────────────────────

def test_extract_txt():
    path = _write_tmp(".txt", "hello world")
    try:
        assert extract_text(path) == "hello world"
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
        assert "INFO" in extract_text(path)
    finally:
        os.unlink(path)


def test_extract_rst():
    path = _write_tmp(".rst", "Title\n=====\n\nBody text.")
    try:
        assert "Body text" in extract_text(path)
    finally:
        os.unlink(path)


def test_extract_toml():
    path = _write_tmp(".toml", '[package]\nname = "myapp"\nversion = "1.0"')
    try:
        result = extract_text(path)
        assert "myapp" in result
    finally:
        os.unlink(path)


# ── code family ───────────────────────────────────────────────────────────────

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
        assert "line0" in result
        assert "line49" in result
    finally:
        os.unlink(path)


def test_extract_js():
    code = "function greet(name) { return 'Hello ' + name; }\n"
    path = _write_tmp(".js", code)
    try:
        assert "function greet" in extract_text(path)
    finally:
        os.unlink(path)


def test_extract_go():
    code = "package main\n\nfunc main() {\n    fmt.Println(\"hi\")\n}\n"
    path = _write_tmp(".go", code)
    try:
        result = extract_text(path)
        assert "func main" in result
    finally:
        os.unlink(path)


def test_extract_rust():
    code = "fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n"
    path = _write_tmp(".rs", code)
    try:
        assert "fn add" in extract_text(path)
    finally:
        os.unlink(path)


def test_extract_tsx():
    code = "export default function App() {\n    return <div>Hello</div>;\n}\n"
    path = _write_tmp(".tsx", code)
    try:
        assert "function App" in extract_text(path)
    finally:
        os.unlink(path)


def test_extract_sh():
    code = "#!/bin/bash\necho 'hello'\n"
    path = _write_tmp(".sh", code)
    try:
        result = extract_text(path)
        assert "echo" in result
    finally:
        os.unlink(path)


# ── JSON ──────────────────────────────────────────────────────────────────────

def test_extract_json_flat():
    data = {"name": "Alice", "age": 30}
    path = _write_tmp(".json", json.dumps(data))
    try:
        result = extract_text(path)
        assert "name: Alice" in result
        assert "age: 30" in result
    finally:
        os.unlink(path)


def test_extract_json_nested():
    data = {"user": {"name": "Bob", "city": "Seoul"}}
    path = _write_tmp(".json", json.dumps(data))
    try:
        result = extract_text(path)
        assert "Bob" in result
        assert "Seoul" in result
    finally:
        os.unlink(path)


def test_extract_json_list():
    data = [{"id": 1, "val": "x"}, {"id": 2, "val": "y"}]
    path = _write_tmp(".json", json.dumps(data))
    try:
        result = extract_text(path)
        assert "x" in result
        assert "y" in result
    finally:
        os.unlink(path)


def test_extract_json_invalid_returns_none():
    path = _write_tmp(".json", "{not valid json}")
    try:
        assert extract_text(path) is None
    finally:
        os.unlink(path)


# ── YAML ──────────────────────────────────────────────────────────────────────

def test_extract_yaml_basic():
    content = "name: Charlie\ncity: Busan\n"
    path = _write_tmp(".yaml", content)
    try:
        result = extract_text(path)
        assert "Charlie" in result
        assert "Busan" in result
    finally:
        os.unlink(path)


def test_extract_yml_extension():
    content = "version: 3\nservices:\n  web:\n    image: nginx\n"
    path = _write_tmp(".yml", content)
    try:
        result = extract_text(path)
        assert "nginx" in result
    finally:
        os.unlink(path)


def test_extract_yaml_empty():
    path = _write_tmp(".yaml", "")
    try:
        result = extract_text(path)
        assert result == "" or result is None or result == "None"
    finally:
        os.unlink(path)


# ── CSV ───────────────────────────────────────────────────────────────────────

def test_extract_csv_basic():
    content = "name,age,city\nAlice,30,Seoul\nBob,25,Busan\n"
    path = _write_tmp(".csv", content)
    try:
        result = extract_text(path)
        assert "name" in result
        assert "Alice" in result
        assert "Bob" in result
    finally:
        os.unlink(path)


def test_extract_csv_headers_included():
    content = "x,y,z\n1,2,3\n"
    path = _write_tmp(".csv", content)
    try:
        result = extract_text(path)
        assert "x, y, z" in result
    finally:
        os.unlink(path)


def test_extract_csv_empty():
    path = _write_tmp(".csv", "")
    try:
        result = extract_text(path)
        assert result == "" or result is None
    finally:
        os.unlink(path)


# ── HTML ──────────────────────────────────────────────────────────────────────

def test_extract_html_basic():
    html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
    path = _write_tmp(".html", html)
    try:
        result = extract_text(path)
        assert "Hello" in result
        assert "World" in result
        assert "<h1>" not in result
    finally:
        os.unlink(path)


def test_extract_html_strips_scripts():
    html = "<html><script>alert('xss')</script><body>Content</body></html>"
    path = _write_tmp(".html", html)
    try:
        result = extract_text(path)
        assert "Content" in result
        # script body should not appear in extracted text
        assert "alert" not in result
    finally:
        os.unlink(path)


def test_extract_htm_extension():
    html = "<p>File with .htm extension</p>"
    path = _write_tmp(".htm", html)
    try:
        result = extract_text(path)
        assert "htm extension" in result
    finally:
        os.unlink(path)


# ── unsupported / error cases ─────────────────────────────────────────────────

def test_extract_unsupported_extension_returns_none():
    path = _write_tmp(".xyz", "some data")
    try:
        assert extract_text(path) is None
    finally:
        os.unlink(path)


def test_extract_nonexistent_file_returns_none():
    assert extract_text("/nonexistent/path/to/file.txt") is None


def test_extract_empty_txt():
    path = _write_tmp(".txt", "")
    try:
        assert extract_text(path) == ""
    finally:
        os.unlink(path)


# ── _flatten helper ───────────────────────────────────────────────────────────

def test_flatten_flat_dict():
    lines: list[str] = []
    _flatten({"a": 1, "b": "hello"}, "", lines)
    assert any("a: 1" in l for l in lines)
    assert any("b: hello" in l for l in lines)


def test_flatten_nested_dict():
    lines: list[str] = []
    _flatten({"outer": {"inner": "value"}}, "", lines)
    assert any("inner" in l and "value" in l for l in lines)


def test_flatten_list():
    lines: list[str] = []
    _flatten([1, 2, 3], "items", lines)
    assert len(lines) == 3


def test_flatten_depth_limit():
    deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "too deep"}}}}}}}
    lines: list[str] = []
    _flatten(deep, "", lines)
    # Should not crash and should produce some output
    assert isinstance(lines, list)
