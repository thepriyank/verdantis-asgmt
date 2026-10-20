"""Load JSON into frozen records. A bad row becomes a flagged record, never an exception."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, NamedTuple

from dq.config import Config
from dq.models import FIELDS, ParsedRecord, ParseIssue
from dq.normalize import clean

_BAD_TYPES = (list, dict, bool)
_RAW_PREVIEW = 200


class IngestError(Exception):
    """The file as a whole cannot be used (unreadable, not JSON, not an array)."""


class IngestResult(NamedTuple):
    records: tuple[ParsedRecord, ...]
    parse_issues: tuple[ParseIssue, ...]


def load_file(path: Path, cfg: Config) -> IngestResult:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise IngestError(f"cannot read {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IngestError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise IngestError(f"{path}: expected a JSON array of records")
    return parse_records(data, cfg)


def parse_records(data: list[Any], cfg: Config) -> IngestResult:
    records = tuple(_parse_row(i, row, cfg) for i, row in enumerate(data))
    issues = tuple(
        ParseIssue(row_index=r.row_index, message=r.parse_error) for r in records if r.parse_error
    )
    return IngestResult(records, issues)


def _parse_row(index: int, row: Any, cfg: Config) -> ParsedRecord:
    if not isinstance(row, dict):
        preview = repr(row)[:_RAW_PREVIEW]
        return ParsedRecord(
            row_index=index,
            raw={"value": preview},
            parse_error=f"row is {type(row).__name__}, expected an object",
        )
    values: dict[str, str | None] = {}
    errors: list[str] = []
    for field in FIELDS:
        value = row.get(field)
        if isinstance(value, _BAD_TYPES):
            errors.append(f"{field} has unsupported type {type(value).__name__}")
            values[field] = None
        else:
            values[field] = clean(value, cfg.missing_tokens)
    return ParsedRecord(
        row_index=index,
        raw=copy.deepcopy(row),
        parse_error="; ".join(errors) or None,
        **values,
    )
