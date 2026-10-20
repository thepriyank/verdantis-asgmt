"""R-001: malformed or incomplete row. Pure presence/type logic, so deterministic."""

from __future__ import annotations

from collections.abc import Sequence

from dq.config import Config
from dq.models import ParsedRecord, ReviewCandidate, Source
from dq.scoring import make_candidate

RULE_ID = "R-001"


def check(records: Sequence[ParsedRecord], cfg: Config) -> list[ReviewCandidate]:
    out: list[ReviewCandidate] = []
    for rec in records:
        if rec.parse_error:
            out.append(_malformed(rec, cfg))
            continue
        missing = [f for f in cfg.required_fields if getattr(rec, f) is None]
        if missing:
            out.append(_incomplete(rec, cfg, missing))
    return out


def _malformed(rec: ParsedRecord, cfg: Config) -> ReviewCandidate:
    return make_candidate(
        rec,
        cfg,
        rule_id=RULE_ID,
        policy_key="R-001.malformed_row",
        issue_type="malformed_row",
        explanation=(
            f"Candidate issue detected: the row could not be read as a record ({rec.parse_error})."
        ),
        evidence={"parse_error": rec.parse_error, "raw": rec.raw},
        suggested_action="Ask the source owner to resend this row in the expected format.",
        source=Source.DETERMINISTIC_RULE,
    )


def _incomplete(rec: ParsedRecord, cfg: Config, missing: list[str]) -> ReviewCandidate:
    key = "R-001.no_item_id" if "item_id" in missing else "R-001.incomplete"
    return make_candidate(
        rec,
        cfg,
        rule_id=RULE_ID,
        policy_key=key,
        issue_type="incomplete_record",
        explanation=(
            "Candidate issue detected: required field(s) missing or blank: "
            + ", ".join(missing)
            + "."
        ),
        evidence={"missing_fields": missing, **{f: rec.raw.get(f) for f in missing}},
        suggested_action="Request the missing value(s) from the source owner; review before use.",
        source=Source.DETERMINISTIC_RULE,
    )
