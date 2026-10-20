from __future__ import annotations

import json
from pathlib import Path

import pytest

from dq.cli import main
from tests.conftest import make_row


def write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "in.json"
    path.write_text(content, encoding="utf-8")
    return path


def test_review_writes_json_and_report(tmp_path: Path) -> None:
    src = write(tmp_path, json.dumps([make_row(manufacturer_part_number="")]))
    out, md = tmp_path / "out.json", tmp_path / "out.md"
    assert main(["review", str(src), "-o", str(out), "--report", str(md)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["candidates"][0]["issue_type"] == "missing_part_number"
    assert data["candidates"][0]["status"] == "needs_review"
    assert "needs review" in md.read_text(encoding="utf-8").lower()


def test_stdout_when_no_output_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = write(tmp_path, json.dumps([make_row()]))
    assert main(["review", str(src)]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["total_records"] == 1


def test_empty_input_exits_zero_with_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["review", str(write(tmp_path, "[]"))]) == 0
    cap = capsys.readouterr()
    assert json.loads(cap.out)["candidates"] == []
    assert "no records" in cap.err.lower()


@pytest.mark.parametrize("content", ["not json", "{}"])
def test_unusable_file_exits_two_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str
) -> None:
    assert main(["review", str(write(tmp_path, content))]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "Traceback" not in err


def test_missing_file_exits_two(tmp_path: Path) -> None:
    assert main(["review", str(tmp_path / "nope.json")]) == 2
