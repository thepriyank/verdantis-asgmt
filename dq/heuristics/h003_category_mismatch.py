"""H-003: description keywords imply a different category than the one recorded."""

from __future__ import annotations

from collections.abc import Sequence

from dq.config import Config
from dq.models import ParsedRecord, ReviewCandidate, Source
from dq.normalize import tokenise
from dq.scoring import make_candidate

RULE_ID = "H-003"


def check(records: Sequence[ParsedRecord], cfg: Config) -> list[ReviewCandidate]:
    lookup = {kw: cat for cat, kws in cfg.category_keywords.items() for kw in kws}
    out: list[ReviewCandidate] = []
    for rec in records:
        if rec.parse_error or not rec.category or not rec.item_description:
            continue
        hit = _expected_category(rec.item_description, lookup)
        if hit and _norm(hit[1]) != _norm(rec.category):
            out.append(_candidate(rec, cfg, *hit))
    return out


def _norm(category: str) -> str:
    # "Mechanical" vs "mechanicals": ignore case and a plural s. The taxonomy itself is an
    # assumption documented in DECISIONS #9.
    return category.casefold().removesuffix("s")


def _expected_category(description: str, lookup: dict[str, str]) -> tuple[str, str] | None:
    """(keyword, category) when the description points to exactly one category."""
    hits: dict[str, str] = {}
    for token in tokenise(description):
        for form in (token, token[:-1] if token.endswith("s") else token):
            if form in lookup:
                hits.setdefault(form, lookup[form])
    # Keywords pointing to different categories are ambiguous: skip rather than guess.
    if len(set(hits.values())) != 1:
        return None
    keyword = next(iter(hits))
    return keyword, hits[keyword]


def _candidate(rec: ParsedRecord, cfg: Config, keyword: str, expected: str) -> ReviewCandidate:
    return make_candidate(
        rec,
        cfg,
        rule_id=RULE_ID,
        policy_key="H-003.mismatch",
        issue_type="category_mismatch_candidate",
        explanation=(
            f"Description contains '{keyword}', which suggests category {expected}, "
            f"but category is {rec.category}."
        ),
        evidence={
            "matched_keyword": keyword,
            "expected_category": expected,
            "category": rec.raw.get("category"),
        },
        suggested_action="Review category assignment before approval.",
        suggested_value=expected,
        source=Source.HEURISTIC,
    )
