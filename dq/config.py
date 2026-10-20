"""Loads config/rules.json into a frozen, validated object."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dq.models import Severity

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "rules.json"


class Policy(BaseModel):
    model_config = ConfigDict(frozen=True)

    severity: Severity
    confidence: float


class Config(BaseModel):
    model_config = ConfigDict(frozen=True)

    missing_tokens: frozenset[str]
    required_fields: tuple[str, ...]
    allowed_uoms: frozenset[str]
    uom_aliases: dict[str, str]
    rule_versions: dict[str, str]
    scoring: dict[str, Policy]


def load_config(path: Path | None = None) -> Config:
    data = json.loads((path or DEFAULT_CONFIG_PATH).read_text(encoding="utf-8"))
    data.pop("_comment", None)
    return Config.model_validate(data)
