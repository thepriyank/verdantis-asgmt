"""H-001: weak or vague description. A heuristic: "vague" is a judgement, not a fact."""

from __future__ import annotations

from collections.abc import Sequence

from dq.config import Config
from dq.models import ParsedRecord, ReviewCandidate, Source
from dq.normalize import tokenise
from dq.scoring import make_candidate

RULE_ID = "H-001"


def check(records: Sequence[ParsedRecord], cfg: Config) -> list[ReviewCandidate]:
    out: list[ReviewCandidate] = []
    for rec in records:
        if rec.parse_error or rec.item_description is None:
            continue
        tokens = tokenise(rec.item_description)
        key = _policy_key(tokens, cfg)
        if key:
            out.append(_candidate(rec, cfg, tokens, key))
    return out


def _policy_key(tokens: list[str], cfg: Config) -> str | None:
    # Any token with a digit (size, rating, part number) counts as a useful attribute.
    if not tokens or any(any(ch.isdigit() for ch in t) for t in tokens):
        return None
    generic = [t in cfg.generic_nouns for t in tokens]
    if len(tokens) == 1 and generic[0]:
        return "H-001.single_noun"
    if len(tokens) <= cfg.vague_max_tokens or all(generic):
        return "H-001.sparse"
    return None


def _candidate(rec: ParsedRecord, cfg: Config, tokens: list[str], key: str) -> ReviewCandidate:
    return make_candidate(
        rec,
        cfg,
        rule_id=RULE_ID,
        policy_key=key,
        issue_type="weak_description",
        explanation=(
            f"Candidate issue detected: description has {len(tokens)} word(s) and no "
            "identifying attribute such as a size, rating or part number."
        ),
        evidence={"item_description": rec.raw.get("item_description"), "tokens": tokens},
        suggested_action="Ask the source owner for a fuller description; review before approval.",
        source=Source.HEURISTIC,
    )
