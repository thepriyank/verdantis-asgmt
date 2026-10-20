"""A-001: normalized description suggestion. AI-assisted, suggestion only, always reviewed."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from dq.ai.guardrails import build_request, validate_response
from dq.ai.suggester import ALLOWED_FIELDS, Suggester
from dq.config import Config
from dq.models import ParsedRecord, ReviewCandidate, Source
from dq.scoring import make_candidate

RULE_ID = "A-001"
log = logging.getLogger(__name__)


def check_with(
    suggester: Suggester, records: Sequence[ParsedRecord], cfg: Config
) -> list[ReviewCandidate]:
    out: list[ReviewCandidate] = []
    for rec in records:
        # Malformed rows and rows without a description are R-001's business; send nothing.
        if rec.parse_error or not rec.item_description:
            continue
        candidate = _suggest_for(suggester, rec, cfg)
        if candidate:
            out.append(candidate)
    return out


def _suggest_for(suggester: Suggester, rec: ParsedRecord, cfg: Config) -> ReviewCandidate | None:
    assert rec.item_description is not None
    try:
        raw = suggester.suggest(build_request(rec))
    except Exception:  # noqa: BLE001 - a provider may fail in any way; the run must go on
        log.warning("suggester failed for row %s; no candidate", rec.row_index)
        return None
    payload = validate_response(raw, rec.item_description, cfg)
    if payload is None:
        if raw is not None:
            log.warning("rejected suggester output for row %s", rec.row_index)
        return None
    return make_candidate(
        rec,
        cfg,
        rule_id=RULE_ID,
        policy_key="A-001.suggestion",
        issue_type="normalized_description_suggestion",
        explanation=f"Suggested description (AI-assisted): {payload.explanation}",
        evidence={
            "item_description": rec.raw.get("item_description"),
            "fields_sent": sorted(ALLOWED_FIELDS),
        },
        suggested_action="Review suggested description before approval.",
        suggested_value=payload.suggested_description,
        source=Source.AI_ASSISTED,
        confidence=payload.confidence,
    )
