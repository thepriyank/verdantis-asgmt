"""H-002: potential duplicate across rows (same manufacturer + same canonical part number)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from dq.config import Config
from dq.models import ParsedRecord, ReviewCandidate, Source
from dq.normalize import canonical_mpn
from dq.scoring import make_candidate

RULE_ID = "H-002"


def check(records: Sequence[ParsedRecord], cfg: Config) -> list[ReviewCandidate]:
    groups: dict[tuple[str, str], list[ParsedRecord]] = defaultdict(list)
    for rec in records:
        mpn = canonical_mpn(rec.manufacturer_part_number)
        if rec.parse_error or not rec.manufacturer or not mpn:
            continue
        groups[(rec.manufacturer.casefold(), mpn)].append(rec)
    out: list[ReviewCandidate] = []
    for (_, mpn), group in groups.items():
        # Same item_id on every row is R-003's finding, not a cross-record duplicate.
        if len(group) > 1 and len({r.item_id for r in group}) > 1:
            out.extend(_candidates(group, mpn, cfg))
    return out


def _candidates(group: list[ParsedRecord], mpn: str, cfg: Config) -> list[ReviewCandidate]:
    return [
        make_candidate(
            rec,
            cfg,
            rule_id=RULE_ID,
            policy_key="H-002.same_mpn",
            issue_type="potential_duplicate",
            explanation=(
                f"Potential duplicate: {len(group) - 1} other row(s) have the same manufacturer "
                f"and part number (matched as {mpn})."
            ),
            evidence={
                "manufacturer": rec.raw.get("manufacturer"),
                "manufacturer_part_number": rec.raw.get("manufacturer_part_number"),
                "canonical_mpn": mpn,
                "matching_rows": [
                    {"source_system": o.source_system, "row_index": o.row_index}
                    for o in group
                    if o is not rec
                ],
            },
            suggested_action="Investigate whether these rows describe the same part; "
            "review before approval.",
            related_item_ids=[
                i for i in dict.fromkeys(o.item_id for o in group if o is not rec) if i
            ],
            source=Source.HEURISTIC,
        )
        for rec in group
    ]
