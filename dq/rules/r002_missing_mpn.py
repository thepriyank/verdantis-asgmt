"""R-002: manufacturer present but manufacturer part number missing."""

from __future__ import annotations

from collections.abc import Sequence

from dq.config import Config
from dq.models import ParsedRecord, ReviewCandidate, Source
from dq.scoring import make_candidate

RULE_ID = "R-002"


def check(records: Sequence[ParsedRecord], cfg: Config) -> list[ReviewCandidate]:
    return [
        make_candidate(
            rec,
            cfg,
            rule_id=RULE_ID,
            policy_key="R-002.missing_mpn",
            issue_type="missing_part_number",
            explanation="Manufacturer is present but manufacturer part number is missing.",
            evidence={
                "manufacturer": rec.raw.get("manufacturer"),
                "manufacturer_part_number": rec.raw.get("manufacturer_part_number"),
            },
            suggested_action="Request manufacturer part number from the source owner.",
            source=Source.DETERMINISTIC_RULE,
        )
        for rec in records
        # Malformed rows are reported once by R-001; their field values are not trustworthy.
        if not rec.parse_error and rec.manufacturer and not rec.manufacturer_part_number
    ]
