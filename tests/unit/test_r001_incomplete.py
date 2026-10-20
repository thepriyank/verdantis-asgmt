from __future__ import annotations

from dq.config import Config
from dq.ingest import parse_records
from dq.models import Severity, Source
from dq.rules import r001_incomplete
from tests.conftest import make_row


def run(rows: list[object], cfg: Config):  # type: ignore[no-untyped-def]
    return r001_incomplete.check(parse_records(rows, cfg).records, cfg)


def test_valid_row_has_no_finding(cfg: Config) -> None:
    assert run([make_row()], cfg) == []


def test_whitespace_item_id_is_high_and_keeps_raw_evidence(cfg: Config) -> None:
    (c,) = run([make_row(item_id="  ")], cfg)
    assert c.rule_id == "R-001"
    assert c.issue_type == "incomplete_record"
    assert c.severity is Severity.HIGH
    assert c.confidence == 1.0
    assert c.item_id is None
    assert c.evidence["item_id"] == "  "
    assert c.evidence["missing_fields"] == ["item_id"]
    assert c.source is Source.DETERMINISTIC_RULE
    assert c.status == "needs_review"


def test_null_like_description_is_medium(cfg: Config) -> None:
    (c,) = run([make_row(item_description="n/a")], cfg)
    assert c.severity is Severity.MEDIUM
    assert c.evidence["missing_fields"] == ["item_description"]
    assert c.item_id == "1001"


def test_several_missing_fields_give_one_candidate(cfg: Config) -> None:
    row = make_row(unit_of_measure=None, source_system="")
    (c,) = run([row], cfg)
    assert c.evidence["missing_fields"] == ["unit_of_measure", "source_system"]


def test_missing_key_entirely_is_incomplete(cfg: Config) -> None:
    row = make_row()
    del row["unit_of_measure"]
    (c,) = run([row], cfg)
    assert c.evidence["missing_fields"] == ["unit_of_measure"]
    assert c.evidence["unit_of_measure"] is None


def test_optional_fields_missing_is_not_r001(cfg: Config) -> None:
    row = make_row(manufacturer=None, manufacturer_part_number="", category="-")
    assert run([row], cfg) == []


def test_non_object_row_is_malformed_high_and_run_continues(cfg: Config) -> None:
    out = run([make_row(item_id="A"), "oops", make_row(item_id="")], cfg)
    assert [(c.record_ref.row_index, c.issue_type) for c in out] == [
        (1, "malformed_row"),
        (2, "incomplete_record"),
    ]
    assert out[0].severity is Severity.HIGH
    assert out[0].evidence["raw"] == {"value": "'oops'"}


def test_unsupported_field_type_is_malformed(cfg: Config) -> None:
    (c,) = run([make_row(category=["Mechanical"])], cfg)
    assert c.issue_type == "malformed_row"
    assert "category has unsupported type list" in c.explanation


def test_finding_id_is_stable_and_distinct_per_row(cfg: Config) -> None:
    rows = [make_row(item_id=""), make_row(item_id="")]
    a = run(rows, cfg)
    b = run(rows, cfg)
    assert [c.finding_id for c in a] == [c.finding_id for c in b]
    assert a[0].finding_id != a[1].finding_id
