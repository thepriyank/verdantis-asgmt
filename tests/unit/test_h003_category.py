from __future__ import annotations

import pytest

from dq.config import Config
from dq.heuristics import h003_category_mismatch
from dq.ingest import parse_records
from dq.models import Severity, Source
from tests.conftest import make_row


def run(rows: list[object], cfg: Config):  # type: ignore[no-untyped-def]
    return h003_category_mismatch.check(parse_records(rows, cfg).records, cfg)


def test_bearing_in_electrical_is_a_candidate(cfg: Config) -> None:
    (c,) = run([make_row(item_description="SKF Bearing 6205 ZZ", category="Electrical")], cfg)
    assert c.rule_id == "H-003"
    assert c.issue_type == "category_mismatch_candidate"
    assert c.severity is Severity.LOW
    assert c.confidence == 0.70
    assert c.source is Source.HEURISTIC
    assert c.suggested_value == "Mechanical"
    assert c.evidence == {
        "matched_keyword": "bearing",
        "expected_category": "Mechanical",
        "category": "Electrical",
    }
    assert "bearing" in c.explanation
    assert "Electrical" in c.explanation
    assert c.suggested_action == "Review category assignment before approval."


@pytest.mark.parametrize("category", ["Mechanical", "mechanical", " MECHANICAL "])
def test_matching_category_is_not_flagged(cfg: Config, category: str) -> None:
    assert run([make_row(category=category)], cfg) == []


def test_plural_keyword_matches(cfg: Config) -> None:
    assert (
        len(run([make_row(item_description="Ball bearings 6205", category="Electrical")], cfg)) == 1
    )


@pytest.mark.parametrize("category", [None, "", "n/a"])
def test_missing_category_is_not_flagged(cfg: Config, category: str | None) -> None:
    assert run([make_row(category=category)], cfg) == []


def test_description_without_keyword_is_not_flagged(cfg: Config) -> None:
    assert run([make_row(item_description="Widget 42", category="Electrical")], cfg) == []


def test_keyword_must_be_a_whole_word(cfg: Config) -> None:
    assert run([make_row(item_description="Nutrition label", category="Electrical")], cfg) == []


def test_conflicting_keywords_are_skipped_as_ambiguous(cfg: Config) -> None:
    desc = "Bearing and fuse kit"
    assert run([make_row(item_description=desc, category="Piping")], cfg) == []


def test_missing_description_or_malformed_row_is_ignored(cfg: Config) -> None:
    assert run([make_row(item_description=None), "junk"], cfg) == []
