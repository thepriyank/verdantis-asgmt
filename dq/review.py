"""Human decisions -> append-only audit log.

Approving a finding records the reviewer's intent for a downstream system. This module never
edits the review file, the decisions file or any item record.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from dq.models import RecordRef, ReviewCandidate


class ReviewFileError(Exception):
    """The review or decisions file cannot be used."""


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    finding_id: str = Field(min_length=1)
    decision: Literal["approve", "reject", "investigate"]
    reviewer: str = Field(min_length=1)
    note: str = ""


class AuditEntry(BaseModel):
    """One decision plus the finding it was made on, so the log is readable on its own."""

    model_config = ConfigDict(frozen=True)

    finding_id: str
    item_id: str | None
    record_ref: RecordRef
    issue_type: str
    rule_id: str
    rule_version: str
    source: str
    severity: str
    confidence: float
    explanation: str
    evidence: dict[str, Any]
    suggested_value: str | None
    decision: str
    reviewer: str
    note: str
    decided_at: str
    # Always False: this tool records intent only and never changes a record.
    change_applied: Literal[False] = False


class AuditError(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    finding_id: str | None
    message: str


class AuditLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    entries: tuple[AuditEntry, ...]
    errors: tuple[AuditError, ...]


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ReviewFileError(f"cannot read {path}: {exc}") from exc


def _index_candidates(review: object) -> dict[str, ReviewCandidate]:
    if not isinstance(review, dict) or not isinstance(review.get("candidates"), list):
        raise ReviewFileError("review file must be an object with a 'candidates' array")
    try:
        found = [ReviewCandidate.model_validate(c) for c in review["candidates"]]
    except ValidationError as exc:
        raise ReviewFileError(
            f"review file has an invalid candidate: {exc.error_count()} error(s)"
        ) from exc
    return {c.finding_id: c for c in found}


def _entry(c: ReviewCandidate, d: Decision, decided_at: str) -> AuditEntry:
    return AuditEntry(
        finding_id=c.finding_id,
        item_id=c.item_id,
        record_ref=c.record_ref,
        issue_type=c.issue_type,
        rule_id=c.rule_id,
        rule_version=c.rule_version,
        source=c.source.value,
        severity=c.severity.value,
        confidence=c.confidence,
        explanation=c.explanation,
        evidence=c.evidence,
        suggested_value=c.suggested_value,
        decision=d.decision,
        reviewer=d.reviewer,
        note=d.note,
        decided_at=decided_at,
    )


def build_audit_log(review: object, decisions: list[Any], decided_at: str) -> AuditLog:
    """Pair each decision with its finding. Bad decisions become errors; the rest still count."""
    by_id = _index_candidates(review)
    entries: list[AuditEntry] = []
    errors: list[AuditError] = []
    for i, raw in enumerate(decisions):
        fid = raw.get("finding_id") if isinstance(raw, dict) else None
        try:
            d = Decision.model_validate(raw)
        except ValidationError as exc:
            errors.append(
                AuditError(
                    index=i,
                    finding_id=fid if isinstance(fid, str) else None,
                    message=f"invalid decision: {exc.errors()[0]['msg']}",
                )
            )
            continue
        if d.finding_id not in by_id:
            errors.append(
                AuditError(index=i, finding_id=d.finding_id, message="unknown finding_id")
            )
            continue
        entries.append(_entry(by_id[d.finding_id], d, decided_at))
    return AuditLog(entries=tuple(entries), errors=tuple(errors))


def to_json_text(log: AuditLog) -> str:
    return json.dumps(log.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
