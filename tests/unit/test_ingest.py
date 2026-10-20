from __future__ import annotations

import json
from pathlib import Path

import pytest

from dq.config import Config
from dq.ingest import IngestError, load_file, parse_records
from tests.conftest import make_row


def test_blank_values_become_none_but_raw_is_kept(cfg: Config) -> None:
    result = parse_records([make_row(manufacturer_part_number="  ", category="n/a")], cfg)
    rec = result.records[0]
    assert rec.manufacturer_part_number is None
    assert rec.category is None
    assert rec.raw["manufacturer_part_number"] == "  "
    assert rec.raw["category"] == "n/a"


def test_numeric_item_id_is_accepted_as_string(cfg: Config) -> None:
    rec = parse_records([make_row(item_id=1001)], cfg).records[0]
    assert rec.item_id == "1001"
    assert rec.parse_error is None


def test_non_object_row_is_flagged_not_raised(cfg: Config) -> None:
    result = parse_records([make_row(), "garbage", 42, None], cfg)
    assert len(result.records) == 4
    assert [i.row_index for i in result.parse_issues] == [1, 2, 3]
    assert result.records[1].item_id is None
    assert "str" in (result.records[1].parse_error or "")


@pytest.mark.parametrize("bad", [["a"], {"x": 1}, True])
def test_unsupported_field_type_is_flagged(cfg: Config, bad: object) -> None:
    rec = parse_records([make_row(manufacturer=bad)], cfg).records[0]
    assert rec.manufacturer is None
    assert "manufacturer has unsupported type" in (rec.parse_error or "")


def test_row_index_follows_input_order(cfg: Config) -> None:
    recs = parse_records([make_row(item_id="a"), make_row(item_id="b")], cfg).records
    assert [(r.row_index, r.item_id) for r in recs] == [(0, "a"), (1, "b")]


def test_raw_is_a_copy_of_the_input(cfg: Config) -> None:
    row = make_row()
    rec = parse_records([row], cfg).records[0]
    row["item_id"] = "changed"
    assert rec.raw["item_id"] == "1001"


def test_load_file_roundtrip(tmp_path: Path, cfg: Config) -> None:
    path = tmp_path / "in.json"
    path.write_text(json.dumps([make_row()]), encoding="utf-8")
    assert load_file(path, cfg).records[0].item_id == "1001"


def test_load_file_empty_array_is_valid(tmp_path: Path, cfg: Config) -> None:
    path = tmp_path / "in.json"
    path.write_text("[]", encoding="utf-8")
    assert load_file(path, cfg).records == ()


@pytest.mark.parametrize("content", ["not json", "{}", '"text"', ""])
def test_load_file_rejects_unusable_files(tmp_path: Path, cfg: Config, content: str) -> None:
    path = tmp_path / "in.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(IngestError):
        load_file(path, cfg)


def test_load_file_missing_path(tmp_path: Path, cfg: Config) -> None:
    with pytest.raises(IngestError):
        load_file(tmp_path / "nope.json", cfg)
