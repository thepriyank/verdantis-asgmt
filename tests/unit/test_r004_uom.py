from __future__ import annotations

import pytest

from dq.config import Config
from dq.ingest import parse_records
from dq.models import Severity, Source
from dq.rules import r004_uom
from tests.conftest import make_row


def run(rows: list[object], cfg: Config):  # type: ignore[no-untyped-def]
    return r004_uom.check(parse_records(rows, cfg).records, cfg)


@pytest.mark.parametrize("uom", ["EA", "PC", "KG", "M", "BOX"])
def test_allowed_codes_are_not_flagged(cfg: Config, uom: str) -> None:
    assert run([make_row(unit_of_measure=uom)], cfg) == []


@pytest.mark.parametrize(
    ("uom", "suggested"),
    [("each", "EA"), ("Each", "EA"), ("ea", "EA"), ("pcs", "PC"), ("kgs", "KG")],
)
def test_alias_is_low_with_suggested_value(cfg: Config, uom: str, suggested: str) -> None:
    (c,) = run([make_row(unit_of_measure=uom)], cfg)
    assert c.rule_id == "R-004"
    assert c.issue_type == "non_standard_unit_of_measure"
    assert c.severity is Severity.LOW
    assert c.confidence == 0.9
    assert c.suggested_value == suggested
    assert c.source is Source.DETERMINISTIC_RULE
    assert c.evidence == {"unit_of_measure": uom}
    assert suggested in c.suggested_action
    assert c.status == "needs_review"


def test_unknown_uom_is_medium_without_suggestion(cfg: Config) -> None:
    (c,) = run([make_row(unit_of_measure="XYZ")], cfg)
    assert c.issue_type == "unsupported_unit_of_measure"
    assert c.severity is Severity.MEDIUM
    assert c.confidence == 1.0
    assert c.suggested_value is None
    assert c.evidence == {"unit_of_measure": "XYZ"}


def test_raw_value_is_kept_as_evidence(cfg: Config) -> None:
    (c,) = run([make_row(unit_of_measure="  each ")], cfg)
    assert c.evidence["unit_of_measure"] == "  each "
    assert c.suggested_value == "EA"


@pytest.mark.parametrize("uom", ["", "  ", None, "n/a"])
def test_missing_uom_is_left_to_r001(cfg: Config, uom: str | None) -> None:
    assert run([make_row(unit_of_measure=uom)], cfg) == []


def test_malformed_row_is_ignored(cfg: Config) -> None:
    assert run(["junk", make_row(unit_of_measure=["EA"])], cfg) == []
