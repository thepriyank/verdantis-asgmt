from __future__ import annotations

import pytest

from dq.config import Config
from dq.ingest import parse_records
from dq.models import Severity, Source
from dq.rules import r002_missing_mpn
from tests.conftest import make_row


def run(rows: list[object], cfg: Config):  # type: ignore[no-untyped-def]
    return r002_missing_mpn.check(parse_records(rows, cfg).records, cfg)


@pytest.mark.parametrize("mpn", ["", "   ", None, "n/a", "NULL", "-"])
def test_manufacturer_without_mpn_is_flagged(cfg: Config, mpn: str | None) -> None:
    (c,) = run([make_row(manufacturer="SKF", manufacturer_part_number=mpn)], cfg)
    assert c.rule_id == "R-002"
    assert c.issue_type == "missing_part_number"
    assert c.severity is Severity.MEDIUM
    assert c.confidence == 0.95
    assert c.source is Source.DETERMINISTIC_RULE
    assert c.item_id == "1001"
    assert c.explanation == "Manufacturer is present but manufacturer part number is missing."
    assert c.suggested_action == "Request manufacturer part number from the source owner."
    assert c.evidence == {"manufacturer": "SKF", "manufacturer_part_number": mpn}


def test_mpn_present_is_not_flagged(cfg: Config) -> None:
    assert run([make_row()], cfg) == []


@pytest.mark.parametrize("mfr", ["", "  ", None, "n/a"])
def test_no_manufacturer_is_not_flagged(cfg: Config, mfr: str | None) -> None:
    assert run([make_row(manufacturer=mfr, manufacturer_part_number="")], cfg) == []


def test_malformed_row_is_left_to_r001(cfg: Config) -> None:
    assert run(["junk"], cfg) == []
