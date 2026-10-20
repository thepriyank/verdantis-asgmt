"""AC15: edge_cases.json must produce exactly the reviewed expected output.

tests/golden/expected_output.json is red-zone: a human reviews the diff and regenerates it
(`make golden`). An agent never rewrites it to make this test pass.
"""

from __future__ import annotations

import json
from pathlib import Path

from dq.config import Config
from dq.ingest import load_file
from dq.pipeline import run_review
from dq.report import to_json

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data" / "samples" / "edge_cases.json"
EXPECTED = Path(__file__).resolve().parent / "expected_output.json"


def test_edge_cases_match_golden_output(cfg: Config) -> None:
    ingest = load_file(INPUT, cfg)
    actual = json.loads(to_json(run_review(ingest.records, ingest.parse_issues, cfg)))
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert actual == expected


def test_golden_covers_every_check_family(cfg: Config) -> None:
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    rules = {c["rule_id"] for c in expected["candidates"]}
    assert {"R-001", "R-002", "R-003", "R-004", "H-001", "H-002", "H-003"} <= rules
