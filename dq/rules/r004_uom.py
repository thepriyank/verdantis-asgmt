"""R-004: unit of measure outside the allowed list, or a known alias of an allowed code."""

from __future__ import annotations

from collections.abc import Sequence

from dq.config import Config
from dq.models import ParsedRecord, ReviewCandidate, Source
from dq.scoring import make_candidate

RULE_ID = "R-004"


def check(records: Sequence[ParsedRecord], cfg: Config) -> list[ReviewCandidate]:
    out: list[ReviewCandidate] = []
    for rec in records:
        # A missing UoM is R-001's finding; malformed rows are reported once there too.
        uom = rec.unit_of_measure
        if rec.parse_error or uom is None or uom in cfg.allowed_uoms:
            continue
        out.append(_candidate(rec, cfg, uom))
    return out


def _alias_target(uom: str, cfg: Config) -> str | None:
    if uom.upper() in cfg.allowed_uoms:
        return uom.upper()
    return cfg.uom_aliases.get(uom.casefold())


def _candidate(rec: ParsedRecord, cfg: Config, uom: str) -> ReviewCandidate:
    target = _alias_target(uom, cfg)
    evidence = {"unit_of_measure": rec.raw.get("unit_of_measure")}
    if target:
        return make_candidate(
            rec,
            cfg,
            rule_id=RULE_ID,
            policy_key="R-004.alias",
            issue_type="non_standard_unit_of_measure",
            explanation=f"Candidate issue detected: unit of measure '{uom}' is not a standard "
            f"code; it resembles '{target}'.",
            evidence=evidence,
            suggested_action=f"Review whether '{target}' is the intended unit of measure "
            "before approval.",
            suggested_value=target,
            source=Source.DETERMINISTIC_RULE,
        )
    return make_candidate(
        rec,
        cfg,
        rule_id=RULE_ID,
        policy_key="R-004.unknown",
        issue_type="unsupported_unit_of_measure",
        explanation=f"Candidate issue detected: unit of measure '{uom}' is not in the "
        "supported list.",
        evidence=evidence,
        suggested_action="Confirm the unit of measure with the source owner; review before "
        "approval.",
        source=Source.DETERMINISTIC_RULE,
    )
