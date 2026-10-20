from __future__ import annotations

from dq.config import Config
from dq.ingest import parse_records
from dq.pipeline import run_review
from tests.conftest import make_row


def review(rows: list[object], cfg: Config):  # type: ignore[no-untyped-def]
    ingest = parse_records(rows, cfg)
    return run_review(ingest.records, ingest.parse_issues, cfg)


def test_sorted_by_severity_then_item_id_then_rule(cfg: Config) -> None:
    rows = [
        make_row(item_id="2", manufacturer_part_number=""),  # R-002 medium
        make_row(item_id="1", manufacturer_part_number=""),  # R-002 medium
        make_row(item_id="", manufacturer_part_number="X1"),  # R-001 high, no id
        make_row(item_id="3", item_description=""),  # R-001 medium
    ]
    out = review(rows, cfg)
    assert [(c.severity.value, c.item_id, c.rule_id) for c in out.candidates] == [
        ("high", None, "R-001"),
        ("medium", "1", "R-002"),
        ("medium", "2", "R-002"),
        ("medium", "3", "R-001"),
    ]


def test_summary_counts(cfg: Config) -> None:
    rows = [make_row(manufacturer_part_number=""), "junk", make_row(item_id="2")]
    out = review(rows, cfg)
    assert out.summary["total_records"] == 3
    assert out.summary["total_candidates"] == 2
    assert out.summary["by_severity"] == {"high": 1, "medium": 1}
    assert out.summary["by_source"] == {"deterministic_rule": 2}
    assert out.summary["by_issue_type"] == {"malformed_row": 1, "missing_part_number": 1}
    assert [p.row_index for p in out.parse_issues] == [1]


def test_empty_input(cfg: Config) -> None:
    out = review([], cfg)
    assert out.candidates == ()
    assert out.summary["total_records"] == 0
    assert out.summary["total_candidates"] == 0
