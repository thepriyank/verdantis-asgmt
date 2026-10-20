"""The boundary to any AI provider: what may be sent, what may come back."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

# The only record fields that may ever leave the process (CLAUDE.md section 6).
ALLOWED_FIELDS: tuple[str, ...] = (
    "item_description",
    "manufacturer",
    "category",
    "unit_of_measure",
)


class AllowlistedFields(BaseModel):
    """Request payload. `extra="forbid"` makes adding a field a deliberate code change."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_description: str | None = None
    manufacturer: str | None = None
    category: str | None = None
    unit_of_measure: str | None = None


class SuggestionPayload(BaseModel):
    """Response contract. Anything that does not fit is rejected, not repaired."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    suggested_description: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class Suggester(Protocol):
    """Implemented by StubSuggester today; a real provider would implement the same method.

    The return type is `object` on purpose: provider output is untrusted until the
    guardrails validate it.
    """

    def suggest(self, fields: AllowlistedFields) -> object: ...
