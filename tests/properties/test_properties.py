"""Safety properties that must hold for any input (AC11-AC14)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from dq.config import Config
from dq.ingest import load_file, parse_records
from dq.models import ReviewCandidate
from dq.pipeline import ReviewResult, run_review
from dq.report import to_json, to_markdown
from tests.conftest import make_row

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "samples" / "sample_input.json"
BANNED = ("fixed", "corrected", "auto-approved", "auto-corrected", "cleaned record")

MESSY: list[Any] = [
    make_row(manufacturer_part_number=""),
    make_row(item_id="  ", item_description=None),
    "junk",
    42,
    None,
    make_row(item_id=1003, manufacturer="n/a", category=["x"]),
    make_row(item_description="rodamiento de bolas ñ", manufacturer_part_number="-"),
]


def review(rows: list[Any], cfg: Config) -> ReviewResult:
    ingest = parse_records(rows, cfg)
    return run_review(ingest.records, ingest.parse_issues, cfg)


def test_input_is_not_mutated(cfg: Config) -> None:
    before = copy.deepcopy(MESSY)
    review(MESSY, cfg)
    assert before == MESSY


def test_no_banned_language_in_outputs(cfg: Config) -> None:
    result = review(MESSY, cfg)
    text = (to_json(result) + to_markdown(result)).lower()
    for word in BANNED:
        assert word not in text


def test_no_banned_language_in_source() -> None:
    files = [*(ROOT / "dq").rglob("*.py"), *(ROOT / "config").glob("*.json")]
    for path in files:
        text = path.read_text(encoding="utf-8").lower()
        for word in BANNED:
            assert word not in text, f"{word!r} in {path.name}"


def test_every_candidate_is_valid_and_needs_review(cfg: Config) -> None:
    result = review(MESSY, cfg)
    assert result.candidates
    for c in result.candidates:
        again = ReviewCandidate.model_validate(c.model_dump(mode="json"))
        assert again == c
        assert c.status == "needs_review"
        assert c.rule_id and c.rule_version and c.source
        assert 0.0 <= c.confidence <= 1.0
        assert set(c.allowed_actions) == {"approve", "reject", "investigate"}
        assert c.explanation and c.suggested_action


def test_json_output_matches_contract(cfg: Config) -> None:
    data = json.loads(to_json(review(MESSY, cfg)))
    assert set(data) == {"summary", "candidates", "parse_issues"}
    assert re.fullmatch(r"[0-9a-f]{12}", data["candidates"][0]["finding_id"])


def test_same_input_gives_identical_output(cfg: Config) -> None:
    assert to_json(review(MESSY, cfg)) == to_json(review(MESSY, cfg))
    a = load_file(SAMPLE, cfg)
    b = load_file(SAMPLE, cfg)
    assert to_json(run_review(*a, cfg)) == to_json(run_review(*b, cfg))


def test_sample_file_runs(cfg: Config) -> None:
    ingest = load_file(SAMPLE, cfg)
    result = run_review(ingest.records, ingest.parse_issues, cfg)
    assert result.summary["total_records"] == 5
    assert any(c.issue_type == "missing_part_number" for c in result.candidates)
