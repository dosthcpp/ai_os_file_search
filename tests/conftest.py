"""
Pytest configuration — add package paths so test modules can import
from packages/core and packages/file-indexer without installation.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "packages" / "core"))
sys.path.insert(0, str(ROOT / "packages" / "file-indexer"))
sys.path.insert(0, str(ROOT / "apps" / "search_api"))
