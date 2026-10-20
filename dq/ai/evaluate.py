"""Offline eval harness for any Suggester.

Run it on every prompt, model or abbreviation-list change. The same cases and gate apply to
the stub today and to a real provider later.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dq.ai.guardrails import validate_response
from dq.ai.suggester import AllowlistedFields, Suggester
from dq.config import Config


class EvalCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    item_description: str
    manufacturer: str | None = None
    category: str | None = None
    unit_of_measure: str | None = None
    # What a steward would accept as the suggestion; None means "nothing to suggest".
    expected: str | None
    # Hostile or instruction-like text that must be treated as plain data.
    adversarial: bool = False


class EvalReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int
    correct: int
    wrong: int
    false_suggestions: int
    missed: int
    rejected_by_guardrails: int
    errors: int
    accuracy: float
    passed: bool


def load_cases(path: Path) -> list[EvalCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array of eval cases")
    return [EvalCase.model_validate(item) for item in data]


def _produce(suggester: Suggester, c: EvalCase, cfg: Config) -> tuple[str | None, str]:
    """(text a steward would see or None, outcome tag)."""
    fields = AllowlistedFields(
        item_description=c.item_description,
        manufacturer=c.manufacturer,
        category=c.category,
        unit_of_measure=c.unit_of_measure,
    )
    try:
        raw = suggester.suggest(fields)
    except Exception:  # noqa: BLE001 - any provider failure is a measured outcome, not a crash
        return None, "error"
    payload = validate_response(raw, c.item_description, cfg)
    if payload is not None:
        return payload.suggested_description, "ok"
    return None, "rejected" if isinstance(raw, dict) and raw else "none"


def run_eval(suggester: Suggester, cases: list[EvalCase], cfg: Config) -> EvalReport:
    counts = {"correct": 0, "wrong": 0, "false": 0, "missed": 0, "rejected": 0, "errors": 0}
    for c in cases:
        shown, tag = _produce(suggester, c, cfg)
        counts["rejected"] += tag == "rejected"
        counts["errors"] += tag == "error"
        if tag == "error":
            continue
        if shown == c.expected:
            counts["correct"] += 1
        elif shown is not None and c.expected is None:
            counts["false"] += 1
        elif shown is None:
            counts["missed"] += 1
        else:
            counts["wrong"] += 1
    total = len(cases)
    accuracy = counts["correct"] / total if total else 0.0
    passed = (
        total > 0
        and accuracy >= cfg.ai_eval_min_accuracy
        and counts["false"] <= cfg.ai_eval_max_false_suggestions
        and counts["errors"] == 0
    )
    return EvalReport(
        total=total,
        correct=counts["correct"],
        wrong=counts["wrong"],
        false_suggestions=counts["false"],
        missed=counts["missed"],
        rejected_by_guardrails=counts["rejected"],
        errors=counts["errors"],
        accuracy=round(accuracy, 4),
        passed=passed,
    )
