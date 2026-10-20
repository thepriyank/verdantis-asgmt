"""Guardrails around the suggester: allowlist before sending, validation after receiving."""

from __future__ import annotations

from pydantic import ValidationError

from dq.ai.suggester import AllowlistedFields, SuggestionPayload
from dq.config import Config
from dq.models import ParsedRecord


def build_request(rec: ParsedRecord) -> AllowlistedFields:
    """Copy only the allowlisted, cleaned fields. Nothing else can be expressed in the model."""
    return AllowlistedFields(
        item_description=rec.item_description,
        manufacturer=rec.manufacturer,
        category=rec.category,
        unit_of_measure=rec.unit_of_measure,
    )


def _squash(text: str) -> str:
    return " ".join(text.casefold().split())


def validate_response(raw: object, original: str, cfg: Config) -> SuggestionPayload | None:
    """Return a safe payload or None. Never raises, never repairs bad output."""
    if not isinstance(raw, dict):
        return None
    try:
        payload = SuggestionPayload.model_validate(raw)
    except ValidationError:
        return None
    if not payload.explanation.strip() or not payload.suggested_description.strip():
        return None
    # A suggestion that only differs in case or spacing carries no information.
    if _squash(payload.suggested_description) == _squash(original):
        return None
    capped = min(payload.confidence, cfg.ai_confidence_cap)
    return payload.model_copy(update={"confidence": capped})
