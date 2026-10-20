from __future__ import annotations

from typing import Any

import pytest

from dq.config import Config, load_config
from dq.ingest import parse_records
from dq.models import ParsedRecord


@pytest.fixture(scope="session")
def cfg() -> Config:
    return load_config()


def make_row(**overrides: Any) -> dict[str, Any]:
    """A fully valid row; tests override only the field under test."""
    row: dict[str, Any] = {
        "item_id": "1001",
        "item_description": "SKF Bearing 6205 ZZ",
        "manufacturer": "SKF",
        "manufacturer_part_number": "6205-ZZ",
        "category": "Mechanical",
        "unit_of_measure": "EA",
        "source_system": "ERP-A",
    }
    row.update(overrides)
    return row


@pytest.fixture
def parse(cfg: Config):  # type: ignore[no-untyped-def]
    def _parse(rows: list[Any]) -> tuple[ParsedRecord, ...]:
        return parse_records(rows, cfg).records

    return _parse
