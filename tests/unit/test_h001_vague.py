from __future__ import annotations

import pytest

from dq.config import Config
from dq.heuristics import h001_vague_description
from dq.ingest import parse_records
from dq.models import Severity, Source
from tests.conftest import make_row


def run(rows: list[object], cfg: Config):  # type: ignore[no-untyped-def]
    return h001_vague_description.check(parse_records(rows, cfg).records, cfg)


@pytest.mark.parametrize("desc", ["bearing", "valve", "BEARING", " Valve. "])
def test_single_generic_noun_is_medium(cfg: Config, desc: str) -> None:
    (c,) = run([make_row(item_description=desc)], cfg)
    assert c.rule_id == "H-001"
    assert c.issue_type == "weak_description"
    assert c.severity is Severity.MEDIUM
    assert c.confidence == 0.85
    assert c.source is Source.HEURISTIC
    assert c.evidence == {"item_description": desc, "tokens": c.evidence["tokens"]}
    assert c.status == "needs_review"


@pytest.mark.parametrize("desc", ["Ball bearing", "rodamiento", "Gate valve"])
def test_short_description_without_attributes_is_low(cfg: Config, desc: str) -> None:
    (c,) = run([make_row(item_description=desc)], cfg)
    assert c.severity is Severity.LOW
    assert c.confidence == 0.6


@pytest.mark.parametrize(
    "desc",
    [
        "SKF Bearing 6205 ZZ",
        "Gate valve 2 inch flanged",
        "Fuse 10A",
        "rodamiento de bolas 6205",
        "Hex bolt stainless steel flanged head",
    ],
)
def test_descriptive_text_is_not_flagged(cfg: Config, desc: str) -> None:
    assert run([make_row(item_description=desc)], cfg) == []


def test_all_generic_nouns_without_attributes_is_flagged(cfg: Config) -> None:
    assert len(run([make_row(item_description="bearing valve pump")], cfg)) == 1


@pytest.mark.parametrize("desc", [None, "", "  ", "n/a"])
def test_missing_description_is_left_to_r001(cfg: Config, desc: str | None) -> None:
    assert run([make_row(item_description=desc)], cfg) == []


def test_malformed_row_is_ignored(cfg: Config) -> None:
    assert run(["junk"], cfg) == []
