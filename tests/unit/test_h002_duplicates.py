from __future__ import annotations

from dq.config import Config
from dq.heuristics import h002_potential_duplicate
from dq.ingest import parse_records
from dq.models import Severity, Source
from tests.conftest import make_row


def run(rows: list[object], cfg: Config):  # type: ignore[no-untyped-def]
    return h002_potential_duplicate.check(parse_records(rows, cfg).records, cfg)


def test_same_manufacturer_and_mpn_in_different_formats_across_systems(cfg: Config) -> None:
    rows = [
        make_row(item_id="1001", manufacturer="SKF", manufacturer_part_number="6205-ZZ"),
        make_row(
            item_id="2002",
            manufacturer=" skf ",
            manufacturer_part_number="6205 zz",
            source_system="ERP-B",
        ),
    ]
    a, b = run(rows, cfg)
    for c, other in ((a, "2002"), (b, "1001")):
        assert c.rule_id == "H-002"
        assert c.issue_type == "potential_duplicate"
        assert c.severity is Severity.MEDIUM
        assert c.confidence == 0.9
        assert c.source is Source.HEURISTIC
        assert c.related_item_ids == (other,)
        assert c.evidence["canonical_mpn"] == "6205ZZ"
    assert a.item_id == "1001"
    assert b.record_ref.source_system == "ERP-B"


def test_different_mpn_is_not_flagged(cfg: Config) -> None:
    rows = [
        make_row(item_id="1", manufacturer_part_number="6205-ZZ"),
        make_row(item_id="2", manufacturer_part_number="6205-2RS"),
    ]
    assert run(rows, cfg) == []


def test_same_mpn_different_manufacturer_is_not_flagged(cfg: Config) -> None:
    rows = [
        make_row(item_id="1", manufacturer="SKF"),
        make_row(item_id="2", manufacturer="FAG"),
    ]
    assert run(rows, cfg) == []


def test_same_item_id_is_left_to_r003(cfg: Config) -> None:
    assert run([make_row(item_id="1"), make_row(item_id="1")], cfg) == []


def test_missing_mpn_or_manufacturer_never_matches(cfg: Config) -> None:
    rows = [
        make_row(item_id="1", manufacturer_part_number=""),
        make_row(item_id="2", manufacturer_part_number="n/a"),
        make_row(item_id="3", manufacturer=None),
        make_row(item_id="4", manufacturer=""),
    ]
    assert run(rows, cfg) == []


def test_three_way_match_lists_the_other_two(cfg: Config) -> None:
    rows = [make_row(item_id=str(i)) for i in (1, 2, 3)]
    out = run(rows, cfg)
    assert [c.related_item_ids for c in out] == [("2", "3"), ("1", "3"), ("1", "2")]


def test_malformed_rows_are_ignored(cfg: Config) -> None:
    assert run(["junk", make_row(item_id="1")], cfg) == []
