"""The single place where severity and confidence are decided, and candidates are assembled."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from dq.config import Config
from dq.models import ParsedRecord, RecordRef, ReviewCandidate, Source


def finding_id(rule_id: str, rec: ParsedRecord) -> str:
    """Stable id from rule + record position, so reruns and golden files line up."""
    key = f"{rule_id}|{rec.source_system}|{rec.row_index}|{rec.item_id}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def make_candidate(
    rec: ParsedRecord,
    cfg: Config,
    *,
    rule_id: str,
    policy_key: str,
    issue_type: str,
    explanation: str,
    evidence: dict[str, Any],
    suggested_action: str,
    source: Source,
    suggested_value: str | None = None,
    related_item_ids: Sequence[str] = (),
) -> ReviewCandidate:
    policy = cfg.scoring[policy_key]
    return ReviewCandidate(
        finding_id=finding_id(rule_id, rec),
        item_id=rec.item_id,
        record_ref=RecordRef(source_system=rec.source_system, row_index=rec.row_index),
        issue_type=issue_type,
        severity=policy.severity,
        confidence=policy.confidence,
        explanation=explanation,
        evidence=evidence,
        suggested_action=suggested_action,
        suggested_value=suggested_value,
        related_item_ids=tuple(related_item_ids),
        source=source,
        rule_id=rule_id,
        rule_version=cfg.rule_versions[rule_id],
    )
