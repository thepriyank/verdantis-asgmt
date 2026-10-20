"""R-003: the same item_id appears on more than one row."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from dq.config import Config
from dq.models import FIELDS, ParsedRecord, ReviewCandidate, Source
from dq.scoring import make_candidate

RULE_ID = "R-003"
# Provenance differs by design between systems, so it is not a conflict.
_COMPARED = tuple(f for f in FIELDS if f not in ("item_id", "source_system"))


def check(records: Sequence[ParsedRecord], cfg: Config) -> list[ReviewCandidate]:
    groups: dict[str, list[ParsedRecord]] = defaultdict(list)
    for rec in records:
        if rec.item_id and not rec.parse_error:
            groups[rec.item_id].append(rec)
    out: list[ReviewCandidate] = []
    for group in groups.values():
        if len(group) > 1:
            out.extend(_candidates_for_group(group, cfg))
    return out


def _candidates_for_group(group: list[ParsedRecord], cfg: Config) -> list[ReviewCandidate]:
    conflicting = [f for f in _COMPARED if len({getattr(r, f) for r in group}) > 1]
    key = "R-003.conflicting" if conflicting else "R-003.identical"
    how = (
        f"with conflicting values in: {', '.join(conflicting)}"
        if conflicting
        else "as identical copies"
    )
    return [
        make_candidate(
            rec,
            cfg,
            rule_id=RULE_ID,
            policy_key=key,
            issue_type="duplicate_item_id",
            explanation=(
                f"Candidate issue detected: item_id {rec.item_id} appears on {len(group)} rows, "
                f"{how}."
            ),
            evidence={
                "conflicting_fields": conflicting,
                "other_rows": [
                    {"source_system": o.source_system, "row_index": o.row_index}
                    for o in group
                    if o is not rec
                ],
            },
            suggested_action="Investigate which row is authoritative before approval.",
            source=Source.DETERMINISTIC_RULE,
        )
        for rec in group
    ]
