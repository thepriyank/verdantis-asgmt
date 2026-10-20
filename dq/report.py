"""JSON output and the short markdown summary for the steward. Candidate language only."""

from __future__ import annotations

import json

from dq.pipeline import ReviewResult


def to_json(result: ReviewResult) -> str:
    return json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"


def to_markdown(result: ReviewResult) -> str:
    s = result.summary
    lines = [
        "# Review candidates",
        "",
        f"{s['total_candidates']} candidate issue(s) detected in {s['total_records']} record(s). "
        "Every candidate needs review; no record has been changed.",
        "",
    ]
    if s["by_severity"]:
        lines += ["| Severity | Count |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in s["by_severity"].items()]
        lines.append("")
    for c in result.candidates:
        who = f"item {c.item_id}" if c.item_id else f"row {c.record_ref.row_index} (no item id)"
        lines += [
            f"## {who}: {c.issue_type}",
            f"- Severity: {c.severity.value} · confidence {c.confidence:.2f} · "
            f"{c.source.value} ({c.rule_id})",
            f"- Why: {c.explanation}",
            f"- Suggested action: {c.suggested_action}",
            "- Status: needs review (approve / reject / investigate)",
            "",
        ]
    return "\n".join(lines)
