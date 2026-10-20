"""Runs every check over frozen records, sorts candidates, builds the summary.

Checks only read records, so the pipeline cannot change the input.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from dq.ai import a001_suggestion
from dq.ai.suggester import Suggester
from dq.config import Config
from dq.heuristics import (
    h001_vague_description,
    h002_potential_duplicate,
    h003_category_mismatch,
)
from dq.models import ParsedRecord, ParseIssue, ReviewCandidate, Severity
from dq.rules import r001_incomplete, r002_missing_mpn, r003_duplicate_id, r004_uom

Check = Callable[[Sequence[ParsedRecord], Config], list[ReviewCandidate]]

# Deterministic rules first; heuristics are added here as their slices land.
CHECKS: tuple[Check, ...] = (
    r001_incomplete.check,
    r002_missing_mpn.check,
    r003_duplicate_id.check,
    r004_uom.check,
    h001_vague_description.check,
    h002_potential_duplicate.check,
    h003_category_mismatch.check,
)

_SEVERITY_RANK = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}


class ReviewResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: dict[str, Any]
    candidates: tuple[ReviewCandidate, ...]
    parse_issues: tuple[ParseIssue, ...]


def _sort_key(c: ReviewCandidate) -> tuple[int, bool, str, str, int]:
    # Records without an id sort after those with one inside the same severity.
    return (
        _SEVERITY_RANK[c.severity],
        c.item_id is None,
        c.item_id or "",
        c.rule_id,
        c.record_ref.row_index,
    )


def _count(values: Sequence[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def run_review(
    records: Sequence[ParsedRecord],
    parse_issues: Sequence[ParseIssue],
    cfg: Config,
    suggester: Suggester | None = None,
) -> ReviewResult:
    found = [c for check in CHECKS for c in check(records, cfg)]
    # The AI layer is opt-in and runs after the rules; it can only add suggestions.
    if suggester is not None:
        found += a001_suggestion.check_with(suggester, records, cfg)
    candidates = tuple(sorted(found, key=_sort_key))
    summary = {
        "total_records": len(records),
        "total_candidates": len(candidates),
        "by_severity": _count([c.severity.value for c in candidates]),
        "by_source": _count([c.source.value for c in candidates]),
        "by_issue_type": _count([c.issue_type for c in candidates]),
    }
    return ReviewResult(summary=summary, candidates=candidates, parse_issues=tuple(parse_issues))
