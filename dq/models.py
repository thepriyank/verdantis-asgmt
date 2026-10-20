"""Frozen domain models. Raw input is parsed into these once; checks only read them."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# The record fields from the brief. Fixed by the data model, so not configuration.
FIELDS: tuple[str, ...] = (
    "item_id",
    "item_description",
    "manufacturer",
    "manufacturer_part_number",
    "category",
    "unit_of_measure",
    "source_system",
)


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Source(StrEnum):
    DETERMINISTIC_RULE = "deterministic_rule"
    HEURISTIC = "heuristic"
    AI_ASSISTED = "ai_assisted_candidate"


class ParsedRecord(BaseModel):
    """One input row. Field values are cleaned (blank -> None); `raw` keeps the original."""

    model_config = ConfigDict(frozen=True)

    row_index: int
    item_id: str | None = None
    item_description: str | None = None
    manufacturer: str | None = None
    manufacturer_part_number: str | None = None
    category: str | None = None
    unit_of_measure: str | None = None
    source_system: str | None = None
    raw: dict[str, Any]
    parse_error: str | None = None


class ParseIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_index: int
    message: str


class RecordRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_system: str | None
    row_index: int


class ReviewCandidate(BaseModel):
    """The output contract (CLAUDE.md section 5). Always needs_review, never an applied change."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str
    item_id: str | None
    record_ref: RecordRef
    issue_type: str
    severity: Severity
    confidence: float
    explanation: str
    evidence: dict[str, Any]
    suggested_action: str
    suggested_value: str | None = None
    related_item_ids: tuple[str, ...] = ()
    source: Source
    rule_id: str
    rule_version: str
    status: Literal["needs_review"] = "needs_review"
    allowed_actions: tuple[Literal["approve", "reject", "investigate"], ...] = (
        "approve",
        "reject",
        "investigate",
    )
