"""Dependency direction from CLAUDE.md section 3: rules and heuristics never import ai/."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dq.cli import main
from tests.conftest import make_row

DQ = Path(__file__).resolve().parents[2] / "dq"


@pytest.mark.parametrize("package", ["rules", "heuristics"])
def test_deterministic_layers_do_not_import_ai(package: str) -> None:
    for path in (DQ / package).glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "dq.ai" not in text, f"{path.name} imports the AI layer"
        assert "from dq import ai" not in text


def test_cli_suggest_flag_is_opt_in(tmp_path: Path) -> None:
    src = tmp_path / "in.json"
    src.write_text(json.dumps([make_row(item_description="BRG BALL 6205")]), encoding="utf-8")
    plain, with_ai = tmp_path / "a.json", tmp_path / "b.json"
    assert main(["review", str(src), "-o", str(plain)]) == 0
    assert main(["review", str(src), "-o", str(with_ai), "--suggest"]) == 0
    off = json.loads(plain.read_text(encoding="utf-8"))
    on = json.loads(with_ai.read_text(encoding="utf-8"))
    assert off["candidates"] == []
    (c,) = on["candidates"]
    assert (c["rule_id"], c["source"], c["status"]) == (
        "A-001",
        "ai_assisted_candidate",
        "needs_review",
    )
    assert c["suggested_value"] == "Bearing BALL 6205"
    assert c["confidence"] <= 0.6
