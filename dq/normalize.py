"""Pure helpers. Used for matching and presentation only; they never rewrite stored values."""

from __future__ import annotations

import re
from collections.abc import Collection
from typing import Any

_MPN_SEPARATORS = re.compile(r"[\s\-_./]+")
_TOKEN = re.compile(r"\w+")


def clean(value: Any, missing_tokens: Collection[str]) -> str | None:
    """Trim a scalar; return None when it counts as missing (blank or a null-like token)."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if not text or text.casefold() in missing_tokens:
        return None
    return text


def canonical_mpn(value: str | None) -> str | None:
    """Matching key for part numbers: uppercase, separators removed. Never shown as a new value."""
    if value is None:
        return None
    key = _MPN_SEPARATORS.sub("", value).upper()
    return key or None


def tokenise(text: str | None) -> list[str]:
    """Unicode-aware lowercase word tokens."""
    if not text:
        return []
    return _TOKEN.findall(text.casefold())
