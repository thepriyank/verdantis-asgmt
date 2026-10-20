from __future__ import annotations

import pytest

from dq.config import Config
from dq.normalize import canonical_mpn, clean, tokenise


@pytest.mark.parametrize(
    "value", [None, "", "   ", "\t\n", "null", "NULL", "N/A", "n/a", "NA", "na", "-", " - "]
)
def test_clean_treats_blank_and_null_like_values_as_missing(value: object, cfg: Config) -> None:
    assert clean(value, cfg.missing_tokens) is None


def test_clean_trims_and_keeps_real_values(cfg: Config) -> None:
    assert clean("  SKF  ", cfg.missing_tokens) == "SKF"


def test_clean_stringifies_numbers(cfg: Config) -> None:
    assert clean(1001, cfg.missing_tokens) == "1001"
    assert clean(1001.0, cfg.missing_tokens) == "1001"


def test_clean_does_not_treat_words_containing_na_as_missing(cfg: Config) -> None:
    assert clean("Navy", cfg.missing_tokens) == "Navy"


@pytest.mark.parametrize(
    "value", ["6205-ZZ", "6205 zz", "6205ZZ", " 6205_zz ", "6205.ZZ", "6205/zz"]
)
def test_canonical_mpn_unifies_format_variants(value: str) -> None:
    assert canonical_mpn(value) == "6205ZZ"


def test_canonical_mpn_none_and_separator_only() -> None:
    assert canonical_mpn(None) is None
    assert canonical_mpn("--") is None


def test_canonical_mpn_keeps_different_parts_different() -> None:
    assert canonical_mpn("6205-2RS") != canonical_mpn("6205-ZZ")


def test_tokenise_is_lowercase_and_unicode_safe() -> None:
    assert tokenise("SKF Bearing 6205-ZZ") == ["skf", "bearing", "6205", "zz"]
    assert tokenise("Rodamiento de bolas ñ") == ["rodamiento", "de", "bolas", "ñ"]
    assert tokenise(None) == []
