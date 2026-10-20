# Item Data-Quality Assistant — review candidates for a human data steward

> Verdantis Agentic Coding Lead assignment · built in a 2-hour time box with Claude Code.

## What it does
Reads item master records (JSON) from several source systems and produces **review candidates**: structured, explainable findings a data steward can approve, reject or investigate. It **never modifies the records**. Every finding is `status: "needs_review"` and says whether it came from a deterministic rule or a heuristic.

## Run it
```
make setup       # uv sync
make demo        # data/samples/sample_input.json -> out/review.json + out/review.md
make check       # ruff + mypy (strict on dq/) + pytest with coverage
```
No `make` (for example plain Windows)? Use the same commands directly:
```
uv sync
uv run python -m dq review data/samples/sample_input.json -o out/review.json --report out/review.md
uv run pytest -q --cov=dq
```
CLI: `python -m dq review <input.json> [-o out.json] [--report out.md]`. JSON goes to stdout when `-o` is omitted. Exit codes: `0` success (including empty input), `2` unreadable file, invalid JSON, a top level that is not an array, or an output path equal to the input. Runs fully offline.

## Sample input → output
Input (the brief's two records):
```json
[{"item_id": "1001", "item_description": "bearing", "manufacturer": "SKF",
  "manufacturer_part_number": "", "category": "Mechanical", "unit_of_measure": "EA", "source_system": "ERP-A"},
 {"item_id": "1002", "item_description": "SKF Bearing 6205 ZZ", "manufacturer": "SKF",
  "manufacturer_part_number": "6205-ZZ", "category": "Electrical", "unit_of_measure": "EA", "source_system": "ERP-B"}]
```
Output, abridged (`out/review.md` has the full steward view):

| item | issue_type | severity | confidence | source | explanation |
|---|---|---|---|---|---|
| 1001 | weak_description | medium | 0.85 | heuristic (H-001) | description has 1 word(s) and no identifying attribute |
| 1001 | missing_part_number | medium | 0.95 | deterministic_rule (R-002) | Manufacturer is present but manufacturer part number is missing. |
| 1002 | category_mismatch_candidate | low | 0.70 | heuristic (H-003) | Description contains 'bearing', which suggests category Mechanical, but category is Electrical. |

A full candidate carries `finding_id`, `record_ref`, `evidence`, `suggested_action`, `suggested_value`, `related_item_ids`, `rule_id`, `rule_version`, `status` and `allowed_actions` (schema: CLAUDE.md §5). `data/samples/edge_cases.json` (16 rows) exercises every check and is locked by a golden test.

## Checks implemented
| Brief # | Check | ID | Source | Status |
|---|---|---|---|---|
| 1 | Missing part number when manufacturer present | R-002 | deterministic_rule | done |
| 2 | Weak or vague description | H-001 | heuristic | done |
| 3 | Duplicate `item_id` (same id, conflicting or identical values) | R-003 | deterministic_rule | done |
| 3 | Potential duplicate across systems (manufacturer + canonical part number) | H-002 | heuristic | done |
| 4 | Category mismatch candidate | H-003 | heuristic | done |
| 5 | Unsupported or non-standard unit of measure (alias gets a suggestion) | R-004 | deterministic_rule | done |
| 7 | Malformed or incomplete row | R-001 | deterministic_rule | done |
| 8, 9 | Severity, confidence, explanation on every finding | `dq/scoring.py` | — | done |
| 6 | Normalized description suggestion (stubbed AI) | A-001 | ai_assisted_candidate | **not built**, design only |

## Design
- **Boundaries:** `cli → pipeline → (rules, heuristics) → normalize, models, scoring`. `rules/` is pure logic and never imports `heuristics/` or `ai/`. Diagram and the real-LLM plug-in plan: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- **Rule vs heuristic:** a rule is decidable from the data (presence, exact keys, an allowlist). A heuristic is a judgement with a signal (vague text, same part number, keywords), so it carries confidence below 1 and says so in `source`.
- **Safety:** input is parsed into frozen models; a bad row becomes an R-001 finding, never an exception. Property tests prove no input mutation, no banned wording ("fixed", "corrected", "auto-approved"…), a valid schema with `needs_review`, and deterministic output.
- **One policy place:** severity and confidence come only from `dq/scoring.py` and `config/rules.json`. UoM allowlist, aliases, generic nouns and category keywords live in `config/`.

## Tests and verification
- **153 tests, 99% coverage of `dq/`** (100% of `dq/rules`, `dq/heuristics`, `dq/normalize.py`); ruff clean; mypy strict clean.
- Unit tests per check (positive, negative, blank/null/malformed edge cases), property tests, a golden test (`data/samples/edge_cases.json` → `tests/golden/expected_output.json`), the brief's example, CLI exit-code tests, and regression tests for every red-team finding.
- Mutation checks: I broke the logic by hand after each slice and confirmed a test fails. An independent red-team agent then tried 41 mutations; 7 survived (5 real gaps now covered, 2 equivalent). Details in [docs/AI_USAGE.md](docs/AI_USAGE.md).
- The golden file is red-zone: a human reviews it and regenerates it; an agent never rewrites it to go green.

## Assumptions & trade-offs
Full log: [docs/DECISIONS.md](docs/DECISIONS.md). The ones that matter most:
- Required fields are `item_id`, `item_description`, `unit_of_measure`, `source_system`; blank means `""`, whitespace, `null`, `n/a`, `na`, `-`.
- Duplicate `item_id` is checked across all systems (high if values conflict, medium if identical).
- The UoM list and aliases, the generic-noun list and the 3-category keyword map are **starter vocabularies** that need a steward's sign-off.
- JSON only; CSV, fuzzy-description duplicates and the audit log were cut for time.
- Committed straight to `main` after each slice (no PR flow) because of the 2 h box.

## How I used AI
Claude Code, steered by `CLAUDE.md` (standards), `docs/AGENT_POLICY.md` (zones: green/amber/red) and a hook that blocks red-zone edits. I wrote the spec and acceptance criteria first, had the AI draft tests and code per slice, and verified with tests, mutation checks and an independent red-team agent. The red-team found three real defects my own tests missed (crash on deeply nested JSON, `-o` able to overwrite the input, a taxonomy assumption in H-003). What was delegated, rejected and changed: [docs/AI_USAGE.md](docs/AI_USAGE.md). Prepared answers to the discussion topics: [docs/DISCUSSION_NOTES.md](docs/DISCUSSION_NOTES.md).

## Status
- **Works now:** JSON ingest, seven checks (R-001 to R-004, H-001 to H-003), scoring, sorted deterministic JSON output, markdown steward report, CLI with clean exit codes, 153 tests.
- **Incomplete:** A-001 normalized-description suggestion and the whole AI layer (`dq/ai/` and `dq/review.py` are placeholders), CSV input, description-similarity duplicates, decision/audit log, HTTP API. Not tested: very large files (the whole file is read into memory).
- **Risks:** word lists are English-only, so non-English or abbreviation-heavy text is missed (for example "Rodamiento de bolas" in the wrong category is not flagged). H-003 assumes the Mechanical/Electrical/Piping taxonomy. A row with an unsupported field type gets only its R-001 finding until it is resent. Manufacturer matching is trim and case-fold only.
- **Next steps:** build `Suggester` + `StubSuggester` + guardrails and A-001 as designed in ARCHITECTURE.md; add CSV ingest; add fuzzy duplicate detection and manufacturer canonicalisation; add a steward decision log; evaluate the heuristics on real steward-labelled data and tune thresholds.
