# CLAUDE.md — Project Operating Manual

> Read this file fully before every task. It is the single source of truth for how we build.
> The brief is in `docs/ASSIGNMENT.md`. If the brief and this file conflict, the brief wins — log the conflict in `docs/DECISIONS.md`.
> This file is red-zone: you (the agent) may propose edits in chat, never make them.

## 0. Context

- **What:** a time-boxed (2 h) assignment for Verdantis — *Agentic Coding Lead, MRO360*.
- **Product slice:** an **item-master data-quality assistant**. Input: item records from several source systems (JSON/CSV). Output: structured **review candidates** for a human data steward. It **never modifies records**; a human approves, rejects or investigates.
- **What reviewers judge:** how we plan, what we delegate to AI, what the human verifies, assumptions, tests, trade-offs. Correctness > breadth. Explainability > cleverness. Human-review safety > automation. Tests > features. Clean boundaries > lots of code.

## 1. Golden rules (never break)

1. **Spec before code.** No implementation until `docs/SPEC.md` has acceptance criteria for the slice.
2. **Plan before editing** anything touching more than 2 files.
3. **Small vertical slices.** Each slice = check(s) + tests + fixture + doc line → commit.
4. **Tests are the contract.** Write the failing test first. Never delete a test or loosen an assertion to go green.
5. **`make check` green before every commit.**
6. **Never mutate input records.** Raw records are parsed into frozen models; checks read, never write. A test proves this.
7. **Candidates, not corrections.** Every finding has `status: "needs_review"`. Banned words in any output or code string: "fixed", "corrected", "auto-approved", "auto-corrected", "cleaned record". Preferred: "candidate issue detected", "suggested action", "needs review", "potential duplicate", "review before approval". A test enforces this.
8. **Deterministic first.** Rules are pure, deterministic and cover anything checkable by logic. Heuristics handle fuzzy signals. The AI layer is a stub behind an interface and can only *suggest*.
9. **Every finding says where it came from:** `source` ∈ `deterministic_rule | heuristic | ai_assisted_candidate`, plus `rule_id` and `rule_version`.
10. **No assumptions hidden in code.** Thresholds, keyword lists and allowed UoMs live in `config/` and are documented. Unclear requirement → simplest reasonable reading, logged in `docs/DECISIONS.md`.
11. **Time-box.** Anything 5 min over a slice's budget → stop, log in README "Known limitations", cut scope.

## 2. Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Fast to write correctly; strong typing with mypy |
| Models | Pydantic v2 (frozen models) | Validated, immutable, JSON-schema export |
| CLI | `argparse` (stdlib) | Zero extra deps |
| Fuzzy matching | `difflib` (stdlib); `rapidfuzz` only if needed and justified | Keep deps tiny |
| API (Could-have) | FastAPI `POST /review` reusing the same pipeline | Shows how it plugs into a product |
| Tests | pytest, pytest-cov | |
| Quality | ruff (lint + format), mypy (strict on `dq/`) | |
| Packaging | uv | Reproducible, fast |

No database, no real LLM, no network calls. Runs fully offline.

## 3. Repository layout

```
.
├── CLAUDE.md
├── README.md                    # reviewer-facing: problem, run, sample I/O, design, AI usage, trade-offs, next steps
├── Makefile
├── pyproject.toml
├── config/
│   ├── rules.yaml|json          # thresholds, severity map, allowed UoMs, UoM aliases
│   └── category_keywords.json   # keyword → expected category (heuristic)
├── dq/
│   ├── models.py                # RawRecord, ParsedRecord, ReviewCandidate, enums
│   ├── ingest.py                # load JSON/CSV → ParsedRecord + row-level parse issues (never raises on bad rows)
│   ├── normalize.py             # PURE helpers: blank→None, trim, MPN canonical form, UoM alias, tokenise
│   ├── rules/                   # deterministic checks, one module per check, source=deterministic_rule
│   ├── heuristics/              # fuzzy checks (vague description, duplicates, category mismatch), source=heuristic
│   ├── ai/                      # Suggester protocol, StubSuggester, guardrails (field allowlist, output validation)
│   ├── scoring.py               # severity + confidence policy in one place
│   ├── pipeline.py              # runs checks, collects candidates, stable sort, never mutates input
│   ├── report.py                # JSON output + human-readable markdown summary
│   ├── review.py                # (Should) apply human decisions file → audit log; original untouched
│   └── cli.py                   # `python -m dq review <input> [-o out.json] [--report out.md]`
├── data/
│   └── samples/                 # sample_input.json, sample_input.csv, edge_cases.json
├── tests/
│   ├── unit/                    # one file per check + normalize
│   ├── golden/                  # input fixture → expected_output.json (exact match)
│   └── properties/              # no-mutation, banned-language, schema, determinism
└── docs/
    ├── ASSIGNMENT.md            # brief, verbatim
    ├── SPEC.md                  # requirements + acceptance criteria
    ├── ARCHITECTURE.md          # pipeline diagram + where a real LLM plugs in
    ├── DECISIONS.md             # assumptions + trade-offs log
    ├── AI_USAGE.md              # what I asked AI, why, how verified, what I rejected/changed
    ├── AGENT_POLICY.md          # what agents may change vs. what needs human review
    └── DISCUSSION_NOTES.md      # prepared answers to the 8 discussion topics
```

Dependency direction: `cli → pipeline → (rules, heuristics, ai) → normalize, models, scoring`. `rules/` never imports `ai/`.

## 4. Domain glossary and check catalogue

Fields: `item_id`, `item_description`, `manufacturer`, `manufacturer_part_number` (MPN), `category`, `unit_of_measure` (UoM), `source_system`.

**Blank handling:** `None`, `""`, whitespace-only, and the strings `"null"`, `"n/a"`, `"na"`, `"-"` (case-insensitive) are all treated as **missing**. Original values are kept untouched for evidence.

**MPN canonical form:** uppercase, strip spaces, `-`, `_`, `.`, `/` → `6205-ZZ`, `6205 zz`, `6205ZZ` all → `6205ZZ`. Used for matching only; never shown as a "corrected" value.

| ID | Check | Source | Default severity | Confidence |
|---|---|---|---|---|
| R-001 | Malformed / incomplete row (missing required field, wrong type, unparseable row) | deterministic_rule | high (no item_id) / medium | 1.0 |
| R-002 | Missing MPN when manufacturer is present | deterministic_rule | medium | 0.95 |
| R-003 | Duplicate `item_id` (same id, conflicting values) | deterministic_rule | high | 1.0 |
| R-004 | Unsupported / suspicious UoM (not in allowlist; alias like "each" → suggest "EA") | deterministic_rule | medium (unknown) / low (alias) | 1.0 / 0.9 |
| H-001 | Weak or vague description (≤ 2 tokens, generic noun only, no attributes) | heuristic | low/medium | 0.6–0.85 |
| H-002 | Potential duplicate across systems (same manufacturer + canonical MPN; or high description similarity) | heuristic | medium/high | 0.9 (MPN) / 0.6–0.8 (text) |
| H-003 | Category mismatch candidate (description keywords imply a different category) | heuristic | low | 0.5–0.75 |
| A-001 | Normalized description suggestion (stubbed AI) | ai_assisted_candidate | low | ≤ 0.6 cap |

Severity: `high` = blocks use of the record; `medium` = likely wrong; `low` = worth a look. Confidence = how sure the *detection* is, not how bad the issue is. Both set only in `dq/scoring.py`.

## 5. ReviewCandidate schema (the output contract)

```json
{
  "finding_id": "deterministic hash of rule_id + record key",
  "item_id": "1001 | null",
  "record_ref": {"source_system": "ERP-A", "row_index": 0},
  "issue_type": "missing_part_number",
  "severity": "low | medium | high",
  "confidence": 0.95,
  "explanation": "Manufacturer is present but manufacturer part number is missing.",
  "evidence": {"manufacturer": "SKF", "manufacturer_part_number": ""},
  "suggested_action": "Request manufacturer part number from the source owner.",
  "suggested_value": null,
  "related_item_ids": [],
  "source": "deterministic_rule | heuristic | ai_assisted_candidate",
  "rule_id": "R-002",
  "rule_version": "1",
  "status": "needs_review",
  "allowed_actions": ["approve", "reject", "investigate"]
}
```

Output = `{"summary": {...counts by issue/severity/source...}, "candidates": [...], "parse_issues": [...]}` sorted by severity desc, then item_id, then rule_id — so output is deterministic.

## 6. AI layer standards (stubbed now, real later)

- `Suggester` is a Protocol; `StubSuggester` is the default and is rule-based/deterministic.
- **Before sending:** only allowlisted fields (`item_description`, `manufacturer`, `category`, `unit_of_measure`) go to the suggester; never `source_system` internals, user names, prices or free-text notes. Record text is passed as *data* (delimited), never as instructions.
- **After receiving:** validate against a Pydantic schema; reject unknown fields; clamp confidence to `AI_CONFIDENCE_CAP` (0.6); require explanation; drop output that contradicts a deterministic rule; on any failure → no candidate, log it.
- AI output is always `source="ai_assisted_candidate"`, `status="needs_review"`, never auto-applied.
- A real provider (`AnthropicSuggester`) would plug in behind the same interface, with timeouts, retries, cost/latency logging and an eval set — documented in ARCHITECTURE.md, not built.

## 7. Code standards

- Type hints everywhere; mypy strict on `dq/`.
- Functions ≤ 40 lines, files ≤ 250 lines; one check per module; each check is `def check(records: Sequence[ParsedRecord], cfg: Config) -> list[ReviewCandidate]`.
- Names from §4. No magic numbers in checks — read from config.
- Bad input never crashes the run: an unparseable row becomes a `parse_issue` / R-001 candidate. Empty input → empty candidates + clear message, exit 0. Unreadable file → clean error, exit 2.
- No bare `except`; no `print` outside `cli.py`; comments explain *why*.

## 8. Testing standards

- Unit test per check: positive, negative, and edge cases from the brief (blank/whitespace, null, very short description, MPN format variants, same item across systems, duplicate item_id, unsupported UoM, non-English/abbreviated text).
- Golden test: `data/samples/edge_cases.json` → `tests/golden/expected_output.json` exact match.
- Property tests: (a) input unchanged after run (deep-copy compare); (b) no banned words in output; (c) every candidate validates against the schema and has `status=="needs_review"`; (d) same input twice → identical output.
- Each important test must fail if the logic is broken (red-team mutation check).
- Target ≥ 90% coverage on `dq/rules`, `dq/heuristics`, `dq/normalize.py`.

## 9. Git standards

- Conventional Commits (`feat:`, `test:`, `fix:`, `docs:`, `refactor:`, `chore:`). One slice = one commit (a few at most); target 6–10 commits.
- Because of the 2 h box (20 min spent before kickoff, last 10 min reserved for the human's final look), there are no branches or PRs: commit each slice straight to `main` after `make check` is green. Logged in DECISIONS.md #0.
- Never commit `.env`, caches, or generated output (except the golden fixture).
- Final tag: `v1.0-submission`.

## 10. Commands

```
make setup    # uv sync
make test     # pytest with coverage
make lint     # ruff check + format check + mypy
make check    # lint + test (must be green before commit)
make demo     # run the CLI on data/samples/sample_input.json → out/review.json + out/review.md
make golden   # regenerate the golden file (HUMAN ONLY, after reviewing the diff)
```

## 11. Definition of Done

Per slice: criteria ticked in SPEC.md · tests added and `make check` green · `/redteam` run · README/DECISIONS updated · AI_USAGE.md line added · committed.

Submission: fresh clone → `make setup && make demo` works · README covers: what works, how to run, sample input/output, tests, assumptions, trade-offs, AI usage, what's incomplete, risks, next steps · tag pushed · repo shared.

## 12. Agent change policy

Full policy: `docs/AGENT_POLICY.md`. Red zone enforced by `.claude/hooks/guard.py`.

| Zone | Paths | Agent may | Human must |
|---|---|---|---|
| 🟢 Green | `dq/cli.py`, `dq/report.py`, `dq/pipeline.py`, `docs/*` (not policy), `README.md`, `data/samples/*` | Create, edit, refactor | Review diff |
| 🟡 Amber | `dq/rules/**`, `dq/heuristics/**`, `dq/scoring.py`, `dq/ai/**`, `config/**`, `tests/**` | Edit with a stated reason; may add tests, never delete or loosen | Approve each file |
| 🔴 Red | `CLAUDE.md`, `.claude/**`, `docs/AGENT_POLICY.md`, `.github/workflows/**`, `tests/golden/expected_output.json`, `.env*` | Propose only | Make the change |

The golden file is red-zone on purpose: an agent must never "fix" a failing golden test by rewriting the expected output.

## 13. Red-team checklist (run `/redteam` before every merge)

1. **Hallucinated logic:** each check does what §4 says; no invented fields; library calls exist.
2. **Weak tests:** assertions check values, not just "no error"; mutate one threshold/operator → a test must fail; no mocking of the function under test.
3. **Product safety:** no mutation of input; no banned language; every finding is `needs_review` with a source.
4. **Robustness:** blank/whitespace/null/malformed rows handled; empty input handled.
5. **Scope:** only slice files touched; no red-zone edits; no new deps without reason.
6. **AI layer:** allowlist enforced; output validated; confidence capped.

Record findings in the commit message and one line in `docs/AI_USAGE.md`.

## 14. How Claude should work here

- Start each task by restating goal + acceptance criteria in 3 bullets, then plan.
- After each slice: run `make check`, show the output, propose the commit message.
- Unsure about a requirement → state the assumption, log it, continue.
- Use subagents: `test-writer` for edge-case tests, `red-teamer` before merge, `reviewer` at the end, `docs-writer` for README, `domain-expert` for data-steward judgement.
- After each slice append to `docs/AI_USAGE.md`: what was delegated, why, how it was verified, what the human changed or rejected.
- Never run destructive commands or push without asking.
