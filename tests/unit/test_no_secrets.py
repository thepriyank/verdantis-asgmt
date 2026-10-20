"""Secret scan that runs with the normal test suite, so CI blocks a leaked key."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "out"}
SKIP_FILES = {"uv.lock"}
# Built from pieces so this file does not match its own patterns.
PATTERNS = {
    "anthropic key": re.compile("sk-" + r"ant-[A-Za-z0-9_\-]{20,}"),
    "aws access key": re.compile("AK" + r"IA[0-9A-Z]{16}"),
    "private key": re.compile("-----BEGIN " + r"[A-Z ]*" + "PRIVATE KEY-----"),
    "quoted credential": re.compile(
        r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9/+_\-]{12,}['\"]"
    ),
}


def scan(root: Path) -> list[str]:
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or SKIP_DIRS & set(rel.parts) or path.name in SKIP_FILES:
            continue
        # Real .env files are git-ignored; only the committed example is in scope.
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits += [f"{rel}: {name}" for name, rx in PATTERNS.items() if rx.search(text)]
    return hits


def test_repository_contains_no_secrets() -> None:
    assert scan(ROOT) == []


def test_scanner_detects_planted_secrets(tmp_path: Path) -> None:
    fake = "API_" + "KEY" + ' = "' + "abcdefghijklmnop1234" + '"\n'
    (tmp_path / "a.py").write_text(fake, encoding="utf-8")
    (tmp_path / "b.txt").write_text("key sk-" + "ant-" + "x" * 30, encoding="utf-8")
    (tmp_path / ".env").write_text(fake.replace("API_KEY", "PASS" + "WORD"), encoding="utf-8")
    hits = scan(tmp_path)
    assert any(h.startswith("a.py") for h in hits)
    assert any(h.startswith("b.txt") for h in hits)
    assert not any(h.startswith(".env") for h in hits)
