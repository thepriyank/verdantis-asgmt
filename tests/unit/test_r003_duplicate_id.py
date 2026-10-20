from __future__ import annotations

from dq.config import Config
from dq.ingest import parse_records
from dq.models import Severity, Source
from dq.rules import r003_duplicate_id
from tests.conftest import make_row


def run(rows: list[object], cfg: Config):  # type: ignore[no-untyped-def]
    return r003_duplicate_id.check(parse_records(rows, cfg).records, cfg)


def test_unique_ids_are_not_flagged(cfg: Config) -> None:
    assert run([make_row(item_id="1"), make_row(item_id="2")], cfg) == []


def test_conflicting_duplicates_are_high_on_each_row_and_cross_referenced(cfg: Config) -> None:
    rows = [
        make_row(item_id="1001", item_description="bearing", source_system="ERP-A"),
        make_row(item_id="1001", item_description="SKF Bearing 6205 ZZ", source_system="ERP-B"),
    ]
    a, b = run(rows, cfg)
    for c in (a, b):
        assert c.rule_id == "R-003"
        assert c.issue_type == "duplicate_item_id"
        assert c.severity is Severity.HIGH
        assert c.confidence == 1.0
        assert c.source is Source.DETERMINISTIC_RULE
        assert c.item_id == "1001"
        assert c.evidence["conflicting_fields"] == ["item_description"]
    assert a.evidence["other_rows"] == [{"source_system": "ERP-B", "row_index": 1}]
    assert b.evidence["other_rows"] == [{"source_system": "ERP-A", "row_index": 0}]
    assert a.finding_id != b.finding_id


def test_identical_copies_are_medium(cfg: Config) -> None:
    rows = [make_row(item_id="7"), make_row(item_id="7")]
    out = run(rows, cfg)
    assert [c.severity for c in out] == [Severity.MEDIUM, Severity.MEDIUM]
    assert out[0].evidence["conflicting_fields"] == []


def test_blank_variants_do_not_count_as_conflict(cfg: Config) -> None:
    rows = [make_row(item_id="7", category=""), make_row(item_id="7", category="n/a")]
    assert run(rows, cfg)[0].severity is Severity.MEDIUM


def test_three_way_duplicate_lists_both_other_rows(cfg: Config) -> None:
    rows = [make_row(item_id="9", category=c) for c in ("A", "B", "C")]
    out = run(rows, cfg)
    assert len(out) == 3
    assert len(out[0].evidence["other_rows"]) == 2
    assert out[0].evidence["conflicting_fields"] == ["category"]


def test_rows_without_id_or_malformed_are_ignored(cfg: Config) -> None:
    rows = [make_row(item_id=""), make_row(item_id=""), "junk", "junk"]
    assert run(rows, cfg) == []


def test_ids_are_compared_after_trimming(cfg: Config) -> None:
    rows = [make_row(item_id=" 5 "), make_row(item_id="5", category="X")]
    assert len(run(rows, cfg)) == 2
