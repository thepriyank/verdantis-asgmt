"""The red-zone PreToolUse hook (.claude/hooks/guard.py) must block protected paths.

guard.py is red-zone, so an agent cannot fix it. The Windows-path cases below are marked
xfail(strict) because the hook currently lets them through (it strips the working directory
with "/" only, so "C:\\proj\\CLAUDE.md" becomes "\\CLAUDE.md" and matches nothing). When a
human applies the proposed fix the strict xfail turns into a failure, which is the reminder to
delete the marks.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "guard.py"
WIN_CWD = "C:\\Projects\\app"
KNOWN_BUG = pytest.mark.xfail(
    strict=True, reason="guard.py fails open on Windows absolute paths; human must patch it"
)


def run_guard(file_path: str, cwd: str) -> int:
    event = json.dumps({"cwd": cwd, "tool_input": {"file_path": file_path}})
    proc = subprocess.run(
        [sys.executable, str(GUARD)], input=event, capture_output=True, text=True, check=False
    )
    return proc.returncode


@pytest.mark.parametrize(
    "path",
    [
        "CLAUDE.md",
        ".claude/hooks/guard.py",
        "docs/AGENT_POLICY.md",
        ".github/workflows/ci.yml",
        ".env",
        "tests/golden/expected_output.json",
    ],
)
def test_relative_red_zone_paths_are_blocked(path: str) -> None:
    assert run_guard(path, WIN_CWD) == 2


@pytest.mark.parametrize(
    "path", ["/work/app/CLAUDE.md", "/work/app/tests/golden/expected_output.json"]
)
def test_posix_absolute_red_zone_paths_are_blocked(path: str) -> None:
    assert run_guard(path, "/work/app") == 2


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(f"{WIN_CWD}\\CLAUDE.md", marks=KNOWN_BUG, id="win-CLAUDE.md"),
        pytest.param(f"{WIN_CWD}\\.claude\\hooks\\guard.py", marks=KNOWN_BUG, id="win-hook"),
        pytest.param(
            f"{WIN_CWD}\\tests\\golden\\expected_output.json", marks=KNOWN_BUG, id="win-golden"
        ),
        pytest.param(f"{WIN_CWD}\\.github\\workflows\\ci.yml", marks=KNOWN_BUG, id="win-workflow"),
        pytest.param("C:/Projects/app/CLAUDE.md", marks=KNOWN_BUG, id="win-forward-slashes"),
    ],
)
def test_windows_absolute_red_zone_paths_are_blocked(path: str) -> None:
    assert run_guard(path, WIN_CWD) == 2


@pytest.mark.parametrize(
    "path",
    ["dq/cli.py", "/work/app/dq/cli.py", f"{WIN_CWD}\\dq\\cli.py", ".env.example", "README.md"],
)
def test_ordinary_files_are_allowed(path: str) -> None:
    assert run_guard(path, WIN_CWD) == 0
