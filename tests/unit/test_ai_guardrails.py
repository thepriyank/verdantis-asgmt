"""AC17: the AI-assisted layer can only suggest, and only through the guardrails."""

from __future__ import annotations

from typing import Any

import pytest

from dq.ai.a001_suggestion import check_with
from dq.ai.guardrails import build_request, validate_response
from dq.ai.stub import StubSuggester
from dq.ai.suggester import ALLOWED_FIELDS, AllowlistedFields
from dq.config import Config
from dq.ingest import parse_records
from dq.models import Severity, Source
from dq.pipeline import run_review
from dq.report import to_json
from tests.conftest import make_row

GOOD = {"suggested_description": "Bearing Ball 6205", "explanation": "expanded abbreviation"}


class Spy:
    """Records exactly what the pipeline hands to a suggester."""

    def __init__(self, response: object = None) -> None:
        self.seen: list[AllowlistedFields] = []
        self.response = response if response is not None else {**GOOD, "confidence": 0.5}

    def suggest(self, fields: AllowlistedFields) -> object:
        self.seen.append(fields)
        return self.response


class Boom:
    def suggest(self, fields: AllowlistedFields) -> object:
        raise TimeoutError("provider down")


def records(cfg: Config, **overrides: Any):  # type: ignore[no-untyped-def]
    return parse_records([make_row(**overrides)], cfg).records


def test_only_allowlisted_fields_reach_the_suggester(cfg: Config) -> None:
    spy = Spy()
    row = make_row(item_description="BRG BALL 6205", price="12.50", notes="call Bob 555-0100")
    check_with(spy, parse_records([row], cfg).records, cfg)
    (sent,) = spy.seen
    assert (
        set(sent.model_dump())
        == set(ALLOWED_FIELDS)
        == {
            "item_description",
            "manufacturer",
            "category",
            "unit_of_measure",
        }
    )
    assert "12.50" not in str(sent) and "Bob" not in str(sent)
    assert "source_system" not in sent.model_dump()


def test_build_request_uses_cleaned_values(cfg: Config) -> None:
    (rec,) = records(cfg, manufacturer="n/a", item_description="  BRG  ")
    assert build_request(rec).model_dump() == {
        "item_description": "BRG",
        "manufacturer": None,
        "category": "Mechanical",
        "unit_of_measure": "EA",
    }


def test_valid_suggestion_becomes_a_capped_candidate(cfg: Config) -> None:
    (rec,) = records(cfg, item_description="BRG BALL 6205")
    (c,) = check_with(Spy({**GOOD, "confidence": 0.99}), [rec], cfg)
    assert c.rule_id == "A-001"
    assert c.issue_type == "normalized_description_suggestion"
    assert c.source is Source.AI_ASSISTED
    assert c.severity is Severity.LOW
    assert c.confidence == cfg.ai_confidence_cap == 0.6
    assert c.suggested_value == "Bearing Ball 6205"
    assert c.status == "needs_review"
    assert c.suggested_action == "Review suggested description before approval."
    assert c.evidence["item_description"] == "BRG BALL 6205"
    assert c.evidence["fields_sent"] == sorted(ALLOWED_FIELDS)


def test_lower_confidence_is_kept(cfg: Config) -> None:
    (rec,) = records(cfg, item_description="BRG BALL 6205")
    (c,) = check_with(Spy({**GOOD, "confidence": 0.3}), [rec], cfg)
    assert c.confidence == 0.3


@pytest.mark.parametrize(
    "response",
    [
        None,
        "just text",
        [],
        {},
        {**GOOD, "confidence": 0.5, "extra": "field"},
        {"suggested_description": "X", "confidence": 0.5},
        {**GOOD, "explanation": "  ", "confidence": 0.5},
        {**GOOD, "suggested_description": "", "confidence": 0.5},
        {**GOOD, "confidence": "high"},
        {**GOOD, "confidence": 1.5},
        {**GOOD, "confidence": -0.1},
    ],
)
def test_invalid_responses_give_no_candidate(cfg: Config, response: object) -> None:
    (rec,) = records(cfg, item_description="BRG BALL 6205")
    spy = Spy(response)
    spy.response = response
    assert check_with(spy, [rec], cfg) == []


def test_suggester_failure_gives_no_candidate_and_no_crash(cfg: Config) -> None:
    (rec,) = records(cfg, item_description="BRG BALL 6205")
    assert check_with(Boom(), [rec], cfg) == []


def test_suggestion_identical_to_original_is_dropped(cfg: Config) -> None:
    (rec,) = records(cfg, item_description="Bearing Ball 6205")
    same = {"suggested_description": "bearing  ball 6205", "explanation": "x", "confidence": 0.5}
    assert check_with(Spy(same), [rec], cfg) == []


def test_malformed_and_description_less_rows_are_never_sent(cfg: Config) -> None:
    spy = Spy()
    rows = ["junk", make_row(item_description=""), make_row(item_description=["x"])]
    check_with(spy, parse_records(rows, cfg).records, cfg)
    assert spy.seen == []


def test_validate_response_clamps_and_returns_none_on_garbage(cfg: Config) -> None:
    ok = validate_response({**GOOD, "confidence": 0.9}, "BRG", cfg)
    assert ok is not None and ok.confidence == 0.6
    assert validate_response(42, "BRG", cfg) is None


def test_stub_expands_abbreviations_deterministically(cfg: Config) -> None:
    stub = StubSuggester(cfg)
    fields = AllowlistedFields(item_description="BRG BALL 6205 2RS SKF")
    first, second = stub.suggest(fields), stub.suggest(fields)
    assert first == second
    assert first is not None
    assert first["suggested_description"] == "Bearing BALL 6205 2RS SKF"
    assert first["confidence"] <= 0.6


def test_stub_has_nothing_to_suggest_for_clean_text(cfg: Config) -> None:
    stub = StubSuggester(cfg)
    assert stub.suggest(AllowlistedFields(item_description="SKF Bearing 6205 ZZ")) is None


def test_pipeline_without_suggester_has_no_ai_candidates(cfg: Config) -> None:
    ingest = parse_records([make_row(item_description="BRG BALL 6205")], cfg)
    result = run_review(ingest.records, ingest.parse_issues, cfg)
    assert all(c.source is not Source.AI_ASSISTED for c in result.candidates)


def test_pipeline_with_stub_adds_a001_and_is_deterministic(cfg: Config) -> None:
    ingest = parse_records([make_row(item_description="BRG BALL 6205")], cfg)
    stub = StubSuggester(cfg)
    a = run_review(ingest.records, ingest.parse_issues, cfg, suggester=stub)
    b = run_review(ingest.records, ingest.parse_issues, cfg, suggester=stub)
    assert [c.rule_id for c in a.candidates] == ["A-001"]
    assert to_json(a) == to_json(b)
    assert a.summary["by_source"] == {"ai_assisted_candidate": 1}


def test_ai_never_changes_the_input(cfg: Config) -> None:
    row = make_row(item_description="BRG BALL 6205")
    before = dict(row)
    ingest = parse_records([row], cfg)
    run_review(ingest.records, ingest.parse_issues, cfg, suggester=StubSuggester(cfg))
    assert row == before
