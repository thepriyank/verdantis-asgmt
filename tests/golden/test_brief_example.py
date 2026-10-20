"""AC10: the two records from the brief produce the brief's two findings."""

from __future__ import annotations

from dq.config import Config
from dq.ingest import parse_records
from dq.pipeline import run_review

BRIEF_INPUT = [
    {
        "item_id": "1001",
        "item_description": "bearing",
        "manufacturer": "SKF",
        "manufacturer_part_number": "",
        "category": "Mechanical",
        "unit_of_measure": "EA",
        "source_system": "ERP-A",
    },
    {
        "item_id": "1002",
        "item_description": "SKF Bearing 6205 ZZ",
        "manufacturer": "SKF",
        "manufacturer_part_number": "6205-ZZ",
        "category": "Electrical",
        "unit_of_measure": "EA",
        "source_system": "ERP-B",
    },
]


def test_brief_example_findings(cfg: Config) -> None:
    ingest = parse_records(BRIEF_INPUT, cfg)
    result = run_review(ingest.records, ingest.parse_issues, cfg)
    by_key = {(c.item_id, c.issue_type): c for c in result.candidates}

    missing = by_key[("1001", "missing_part_number")]
    assert (missing.severity.value, missing.confidence) == ("medium", 0.95)
    assert missing.source.value == "deterministic_rule"
    assert missing.explanation == "Manufacturer is present but manufacturer part number is missing."
    assert missing.suggested_action == "Request manufacturer part number from the source owner."

    mismatch = by_key[("1002", "category_mismatch_candidate")]
    assert (mismatch.severity.value, mismatch.confidence) == ("low", 0.70)
    assert mismatch.source.value == "heuristic"
    assert "Electrical" in mismatch.explanation

    assert all(c.status == "needs_review" for c in result.candidates)
