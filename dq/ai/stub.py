"""StubSuggester: deterministic, offline default. A real provider implements the same Protocol."""

from __future__ import annotations

import re

from dq.ai.suggester import AllowlistedFields
from dq.config import Config

_TOKEN = re.compile(r"\w+|\W+")


class StubSuggester:
    """Expands abbreviations from config; returns None when there is nothing to propose."""

    def __init__(self, cfg: Config) -> None:
        self._abbreviations = cfg.ai_abbreviations
        self._confidence = cfg.ai_confidence_cap

    def suggest(self, fields: AllowlistedFields) -> dict[str, object] | None:
        text = fields.item_description
        if not text:
            return None
        parts = [self._abbreviations.get(p.casefold(), p) for p in _TOKEN.findall(text)]
        proposed = "".join(parts)
        if proposed == text:
            return None
        return {
            "suggested_description": proposed,
            "explanation": "Abbreviations expanded using the configured abbreviation list.",
            "confidence": self._confidence,
        }
