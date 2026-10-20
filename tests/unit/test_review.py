"""Human decisions -> audit log. Approving records intent only; nothing is modified."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from dq.cli import main
from dq.config import Config
from dq.ingest import parse_records
from dq.pipeline import run_review
from dq.report import to_json
from dq.review import ReviewFileError, build_audit_log, to_json_text
from tests.conftest import make_row

WHEN = "2026-10-20T12:00:00+00:00"


@pytest.fixture
def review_doc(cfg: Config) -> dict[str, Any]:
    ingest = parse_records([make_row(manufacturer_part_number=""), make_row(item_id="")], cfg)
    return json.loads(to_json(run_review(ingest.records, ingest.parse_issues, cfg)))  # type: ignore[no-any-return]


def fid(doc: dict[str, Any], rule_id: str) -> str:
    return next(c["finding_id"] for c in doc["candidates"] if c["rule_id"] == rule_id)


def test_decision_becomes_an_audit_entry_with_nothing_applied(review_doc: dict[str, Any]) -> None:
    decisions = [
        {
            "finding_id": fid(review_doc, "R-002"),
            "decision": "approve",
            "reviewer": "pk",
            "note": "ok",
        }
    ]
    log = build_audit_log(review_doc, decisions, WHEN)
    assert log.errors == ()
    (e,) = log.entries
    assert (e.decision, e.reviewer, e.note, e.decided_at) == ("approve", "pk", "ok", WHEN)
    assert (e.rule_id, e.rule_version, e.issue_type, e.item_id) == (
        "R-002",
        "1",
        "missing_part_number",
        "1001",
    )
    assert e.source == "deterministic_rule"
    assert e.evidence["manufacturer"] == "SKF"
    assert e.change_applied is False


@pytest.mark.parametrize("decision", ["approve", "reject", "investigate"])
def test_all_three_decisions_are_accepted(review_doc: dict[str, Any], decision: str) -> None:
    d = [{"finding_id": fid(review_doc, "R-002"), "decision": decision, "reviewer": "pk"}]
    assert build_audit_log(review_doc, d, WHEN).entries[0].decision == decision


def test_unknown_finding_is_an_error_entry_not_a_crash(review_doc: dict[str, Any]) -> None:
    decisions = [
        {"finding_id": "nope", "decision": "reject", "reviewer": "pk"},
        {"finding_id": fid(review_doc, "R-001"), "decision": "investigate", "reviewer": "pk"},
    ]
    log = build_audit_log(review_doc, decisions, WHEN)
    assert [e.rule_id for e in log.entries] == ["R-001"]
    (err,) = log.errors
    assert (err.index, err.finding_id) == (0, "nope")
    assert "unknown finding_id" in err.message


BAD_DECISIONS: list[dict[str, Any] | str | int] = [
    "text",
    42,
    {},
    {"decision": "maybe"},
    {"decision": "approve", "reviewer": None},
    {"decision": "approve", "reviewer": ""},
    {"decision": "approve", "reviewer": "pk", "extra": 1},
    {"decision": "approve", "reviewer": "pk", "note": 5},
]


@pytest.mark.parametrize("bad", BAD_DECISIONS)
def test_invalid_decisions_are_reported_not_applied(
    review_doc: dict[str, Any], bad: dict[str, Any] | str | int
) -> None:
    # Use a REAL finding id so only the validation can reject the decision.
    if isinstance(bad, dict):
        bad = {"finding_id": fid(review_doc, "R-002"), "reviewer": "pk", **bad}
    log = build_audit_log(review_doc, [bad], WHEN)
    assert log.entries == ()
    (err,) = log.errors
    assert "unknown finding_id" not in err.message


def test_inputs_are_not_mutated(review_doc: dict[str, Any]) -> None:
    decisions = [{"finding_id": fid(review_doc, "R-002"), "decision": "approve", "reviewer": "pk"}]
    before = (copy.deepcopy(review_doc), copy.deepcopy(decisions))
    build_audit_log(review_doc, decisions, WHEN)
    assert (review_doc, decisions) == before


def test_log_is_deterministic_and_append_only(review_doc: dict[str, Any]) -> None:
    f = fid(review_doc, "R-002")
    decisions = [
        {"finding_id": f, "decision": "investigate", "reviewer": "a"},
        {"finding_id": f, "decision": "approve", "reviewer": "b"},
    ]
    one = to_json_text(build_audit_log(review_doc, decisions, WHEN))
    two = to_json_text(build_audit_log(review_doc, decisions, WHEN))
    assert one == two
    entries = json.loads(one)["entries"]
    assert [e["decision"] for e in entries] == ["investigate", "approve"]


@pytest.mark.parametrize("doc", [[], {}, {"candidates": "x"}, {"candidates": [{"bad": 1}]}])
def test_unusable_review_file_raises(doc: object) -> None:
    with pytest.raises(ReviewFileError):
        build_audit_log(doc, [], WHEN)  # type: ignore[arg-type]


def write(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_cli_apply_decisions_end_to_end(tmp_path: Path, review_doc: dict[str, Any]) -> None:
    review = write(tmp_path / "review.json", review_doc)
    original = review.read_text(encoding="utf-8")
    decisions = write(
        tmp_path / "d.json",
        [{"finding_id": fid(review_doc, "R-002"), "decision": "approve", "reviewer": "pk"}],
    )
    out = tmp_path / "audit.json"
    args = ["apply-decisions", str(review), str(decisions), "-o", str(out), "--decided-at", WHEN]
    assert main(args) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["entries"][0]["decided_at"] == WHEN
    assert review.read_text(encoding="utf-8") == original


def test_cli_errors_exit_two_and_never_overwrite_inputs(
    tmp_path: Path, review_doc: dict[str, Any]
) -> None:
    review = write(tmp_path / "review.json", review_doc)
    decisions = write(tmp_path / "d.json", [])
    assert main(["apply-decisions", str(tmp_path / "none.json"), str(decisions)]) == 2
    assert main(["apply-decisions", str(review), str(tmp_path / "none.json")]) == 2
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert main(["apply-decisions", str(bad), str(decisions)]) == 2
    assert main(["apply-decisions", str(review), str(decisions), "-o", str(review)]) == 2
    assert main(["apply-decisions", str(review), str(decisions), "-o", str(decisions)]) == 2
    assert json.loads(review.read_text(encoding="utf-8")) == review_doc


def test_decisions_file_must_be_an_array(tmp_path: Path, review_doc: dict[str, Any]) -> None:
    review = write(tmp_path / "review.json", review_doc)
    decisions = write(tmp_path / "d.json", {"finding_id": "x"})
    assert main(["apply-decisions", str(review), str(decisions)]) == 2
