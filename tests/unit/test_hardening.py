"""Regression tests for the red-team findings on S1-S4."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dq.cli import main
from dq.config import Config
from dq.heuristics import h001_vague_description, h003_category_mismatch
from dq.ingest import IngestError, load_file, parse_records
from dq.pipeline import run_review
from dq.report import to_json
from dq.rules import r001_incomplete
from tests.conftest import make_row


def review(rows: list[object], cfg: Config):  # type: ignore[no-untyped-def]
    ingest = parse_records(rows, cfg)
    return run_review(ingest.records, ingest.parse_issues, cfg)


def test_deeply_nested_json_is_a_clean_ingest_error(tmp_path: Path, cfg: Config) -> None:
    path = tmp_path / "deep.json"
    path.write_text("[" * 200_000, encoding="utf-8")
    with pytest.raises(IngestError):
        load_file(path, cfg)
    assert main(["review", str(path)]) == 2


@pytest.mark.parametrize("flag", ["-o", "--report"])
def test_output_may_not_overwrite_the_input(tmp_path: Path, flag: str) -> None:
    src = tmp_path / "in.json"
    original = json.dumps([make_row()])
    src.write_text(original, encoding="utf-8")
    assert main(["review", str(src), flag, str(src)]) == 2
    assert src.read_text(encoding="utf-8") == original


def test_nan_item_id_is_malformed_not_present(tmp_path: Path, cfg: Config) -> None:
    path = tmp_path / "nan.json"
    path.write_text(
        '[{"item_id": NaN, "item_description": "x", "unit_of_measure": "EA", '
        '"source_system": "S"}]',
        encoding="utf-8",
    )
    (c,) = run_review(*load_file(path, cfg), cfg).candidates
    assert c.issue_type == "malformed_row"
    assert "item_id has unsupported type" in c.explanation


def test_bom_prefixed_file_is_read(tmp_path: Path, cfg: Config) -> None:
    path = tmp_path / "bom.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps([make_row()]).encode("utf-8"))
    assert load_file(path, cfg).records[0].item_id == "1001"


def test_non_ascii_text_is_written_as_is(cfg: Config) -> None:
    out = to_json(review([make_row(item_description="轴承", item_id="")], cfg))
    assert "轴承" in out


def test_r001_evidence_is_a_copy_of_the_raw_row(cfg: Config) -> None:
    records = parse_records(["junk"], cfg).records
    (c,) = r001_incomplete.check(records, cfg)
    c.evidence["raw"]["value"] = "tampered"
    assert records[0].raw["value"] == "'junk'"


def test_malformed_row_is_reported_once_not_by_other_checks(cfg: Config) -> None:
    row = make_row(category=["x"], manufacturer="SKF", manufacturer_part_number="")
    out = review([row], cfg)
    assert [c.rule_id for c in out.candidates] == ["R-001"]


def test_vague_boundary_is_two_tokens(cfg: Config) -> None:
    two = h001_vague_description.check(
        parse_records([make_row(item_description="Blue ring")], cfg).records, cfg
    )
    three = h001_vague_description.check(
        parse_records([make_row(item_description="Blue rubber ring")], cfg).records, cfg
    )
    assert len(two) == 1
    assert three == []


def test_records_without_id_sort_after_those_with_one_at_same_severity(cfg: Config) -> None:
    rows = [
        make_row(item_id=""),  # R-001 high, no id
        make_row(item_id="9", category="A"),  # R-003 high pair
        make_row(item_id="9", category="B"),
    ]
    high = [c.item_id for c in review(rows, cfg).candidates if c.severity.value == "high"]
    assert high == ["9", "9", None]


@pytest.mark.parametrize("category", ["Mechanicals", "MECHANICAL"])
def test_category_comparison_ignores_case_and_plural_s(cfg: Config, category: str) -> None:
    rec = parse_records([make_row(category=category)], cfg).records
    assert h003_category_mismatch.check(rec, cfg) == []


def test_gauge_is_no_longer_an_ambiguous_piping_keyword(cfg: Config) -> None:
    row = make_row(item_description="Pressure gauge 0-10 bar", category="Instrumentation")
    assert h003_category_mismatch.check(parse_records([row], cfg).records, cfg) == []
