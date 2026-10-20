"""Every finding is labelled with the layer that produced it (discussion topic 6)."""

from __future__ import annotations

from pathlib import Path

from dq.ai.stub import StubSuggester
from dq.config import Config
from dq.ingest import load_file
from dq.models import Source
from dq.pipeline import run_review

EDGE = Path(__file__).resolve().parents[2] / "data" / "samples" / "edge_cases.json"
EXPECTED_SOURCE = {
    "R": Source.DETERMINISTIC_RULE,
    "H": Source.HEURISTIC,
    "A": Source.AI_ASSISTED,
}


def test_source_matches_the_layer_that_produced_each_finding(cfg: Config) -> None:
    ingest = load_file(EDGE, cfg)
    result = run_review(ingest.records, ingest.parse_issues, cfg, StubSuggester(cfg))
    prefixes = {c.rule_id[0] for c in result.candidates}
    assert prefixes == {"R", "H", "A"}, "edge cases must exercise all three layers"
    for c in result.candidates:
        assert c.source is EXPECTED_SOURCE[c.rule_id[0]], c.rule_id


def test_only_ai_findings_depend_on_a_suggester(cfg: Config) -> None:
    ingest = load_file(EDGE, cfg)
    without = run_review(ingest.records, ingest.parse_issues, cfg)
    with_ai = run_review(ingest.records, ingest.parse_issues, cfg, StubSuggester(cfg))
    assert {c.rule_id[0] for c in without.candidates} == {"R", "H"}
    extra = [c for c in with_ai.candidates if c not in without.candidates]
    assert extra and all(c.rule_id == "A-001" for c in extra)


def test_ai_confidence_is_capped(cfg: Config) -> None:
    ingest = load_file(EDGE, cfg)
    result = run_review(ingest.records, ingest.parse_issues, cfg, StubSuggester(cfg))
    ai = [c.confidence for c in result.candidates if c.rule_id[0] == "A"]
    assert ai and max(ai) <= cfg.ai_confidence_cap
