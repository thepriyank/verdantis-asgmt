# SPEC — Item-master data-quality assistant (review-candidate slice)

## Goal
Read item-master records from several source systems and produce **structured review candidates** for a human data steward. Each candidate says which record, what issue, why, how severe and how confident, what the steward may do, and where the finding came from (deterministic rule, heuristic, or AI-assisted). The tool **never modifies records**. Every finding is `needs_review`.

## Non-goals (this 2 h time box)
- Real LLM or any network call (the AI layer is a stub behind an interface).
- Database, UI, auth, multi-user workflow.
- Applying any suggestion to data (no auto-correct, ever).
- Translation or abbreviation expansion of non-English text.
- CSV ingest, description-similarity duplicates, HTTP API (Could, see MoSCoW). Not built.

## Input contract
- A JSON file whose top level is an **array of objects**.
- Fields: `item_id`, `item_description`, `manufacturer`, `manufacturer_part_number`, `category`, `unit_of_measure`, `source_system`. Unknown extra fields are ignored and never passed to the AI layer.
- **Required:** `item_id`, `item_description`, `unit_of_measure`, `source_system` (DECISIONS #2).
- **Missing** = `None`, `""`, whitespace-only, or `"null"` / `"n/a"` / `"na"` / `"-"` (case-insensitive). Raw values are kept as evidence (DECISIONS #10).
- A numeric `item_id` is accepted as a string. A list, dict, bool or NaN value, or a non-object element, becomes a `parse_issue` + R-001 high; no other check reports on that row (DECISIONS #11, #18).
- Records are parsed into **frozen** Pydantic models. The input object is never mutated.

## Output contract (see CLAUDE.md §5)
```json
{
  "summary": {"total_records": 2, "total_candidates": 3,
              "by_severity": {...}, "by_source": {...}, "by_issue_type": {...}},
  "candidates": [ReviewCandidate, ...],
  "parse_issues": [{"row_index": 3, "message": "..."}]
}
```
- `ReviewCandidate` fields are exactly as in CLAUDE.md §5. `status` is always `"needs_review"` and `allowed_actions` is always `["approve","reject","investigate"]`.
- Sort: severity desc (high > medium > low), then `item_id` (nulls last), then `rule_id`, then `row_index`. Same input → byte-identical output.
- Banned words never appear: "fixed", "corrected", "auto-approved", "auto-corrected", "cleaned record".

## CLI surface
```
python -m dq review <input.json> [-o out.json] [--report out.md] [--suggest]
```
- Writes the JSON to stdout when `-o` is not given. `--report` writes a short markdown summary for the steward.
- `--suggest` (off by default) runs the offline AI-assisted stub and adds A-001 candidates.
- Exit 0 on success, including empty input (`[]` -> empty candidates + message on stderr).
- Exit 2 on an unreadable file, invalid JSON, a top level that is not an array, or an output path equal to the input (clean message, no traceback).

```
python -m dq apply-decisions <review.json> <decisions.json> [-o audit.json] [--decided-at TS]
```
- Records reviewer decisions (approve / reject / investigate) in an append-only audit log. Intent only: `change_applied` is always false and no record is edited (DECISIONS #22).
- Exit 2 on unusable files or an output path equal to an input. Bad decisions are listed under `errors`; exit stays 0.

```
python -m dq eval-suggester [--cases cases.json]
```
- Runs the suggester over `data/eval/suggester_cases.json` and exits 0 (gate passed), 1 (accuracy or false-suggestion limit missed) or 2 (unusable cases file) (DECISIONS #24).

## Check catalogue (CLAUDE.md §4)
| ID | Brief # | Check | Source | Severity | Confidence |
|---|---|---|---|---|---|
| R-001 | 7 | Malformed / incomplete row | deterministic_rule | high (no item_id / bad row) · medium | 1.0 |
| R-002 | 1 | Missing MPN when manufacturer present | deterministic_rule | medium | 0.95 |
| R-003 | 3 | Duplicate `item_id` | deterministic_rule | high (conflicting) · medium (identical) | 1.0 |
| R-004 | 5 | Unsupported / alias UoM | deterministic_rule | medium (unknown) · low (alias) | 1.0 · 0.9 |
| H-001 | 2 | Weak / vague description | heuristic | low · medium | 0.6–0.85 |
| H-002 | 3 | Potential duplicate across rows (mfr + canonical MPN) | heuristic | medium | 0.9 |
| H-003 | 4 | Category mismatch candidate | heuristic | low | 0.70 |
| A-001 | 6 | Normalized description suggestion (offline stub, opt-in `--suggest`) | ai_assisted_candidate | low | ≤ 0.6 |

Brief #8 (confidence + severity) and #9 (explanation) are part of every candidate, set centrally in `dq/scoring.py`.

## Requirements & acceptance criteria
| ID | Requirement (brief #) | Acceptance criteria (Given / When / Then) | Test | Done |
|----|-----------------------|--------------------------------------------|------|------|
| AC1 | R-001 incomplete row (7) | **Given** a row whose `item_id` is `"  "` **when** reviewed **then** one R-001 candidate, severity high, evidence shows the raw `"  "` | `tests/unit/test_r001_incomplete.py` | [x] |
| AC2 | R-001 malformed row (7, R5) | **Given** an array with a string element between two valid rows **when** reviewed **then** a `parse_issue` and an R-001 high are emitted for it, and both valid rows are still checked | same | [x] |
| AC3 | R-002 missing MPN (1) | **Given** manufacturer "SKF" and MPN `""` / `"n/a"` / `null` **when** reviewed **then** R-002, severity medium, confidence 0.95, explanation "Manufacturer is present but manufacturer part number is missing." | `tests/unit/test_r002_missing_mpn.py` | [x] |
| AC4 | R-002 negative | **Given** both manufacturer and MPN blank, or both present **when** reviewed **then** no R-002 | same | [x] |
| AC5 | R-003 duplicate id (3) | **Given** two rows with `item_id` 1001 and different descriptions **when** reviewed **then** R-003 high on each row, each listing the other in `related_item_ids`/evidence; identical copies → medium | `tests/unit/test_r003_duplicate_id.py` | [x] |
| AC6 | R-004 UoM (5) | **Given** UoM `"each"` / `"XYZ"` / `"EA"` **when** reviewed **then** low + `suggested_value "EA"` / medium, no suggested value / no candidate | `tests/unit/test_r004_uom.py` | [x] |
| AC7 | H-001 vague description (2) | **Given** descriptions `"bearing"`, `"valve"`, `"SKF Bearing 6205 ZZ"` **when** reviewed **then** H-001 (source heuristic) on the first two only | `tests/unit/test_h001_vague.py` | [x] |
| AC8 | H-002 potential duplicate (3) | **Given** ERP-A `SKF / "6205-ZZ"` and ERP-B `skf / "6205 zz"` with different item_ids **when** reviewed **then** `potential_duplicate` on both, confidence 0.9, each in the other's `related_item_ids` | `tests/unit/test_h002_duplicates.py` | [x] |
| AC9 | H-003 category mismatch (4) | **Given** "SKF Bearing 6205 ZZ" with category Electrical **when** reviewed **then** H-003 low, confidence 0.70, evidence names the keyword "bearing"; with category Mechanical → none | `tests/unit/test_h003_category.py` | [x] |
| AC10 | Brief example (R2) | **Given** the brief's 2-record example **when** reviewed **then** output contains `missing_part_number` for 1001 and `category_mismatch_candidate` for 1002 with the brief's severity/confidence | `tests/golden/test_brief_example.py` | [x] |
| AC11 | No mutation (R7) | **Given** any input list **when** reviewed **then** it deep-equals its pre-run deep copy | `tests/properties/test_properties.py::test_input_is_not_mutated` | [x] |
| AC12 | Candidate language (R3) | **Given** any input **when** reviewed **then** the serialized output (and the JSON/markdown report) contains no banned word | `tests/properties/test_properties.py` (banned language, outputs and source) | [x] |
| AC13 | Schema + provenance (R2, R4) | **Given** any input **when** reviewed **then** every candidate validates against `ReviewCandidate`, has `status=="needs_review"`, a `source`, `rule_id` and `rule_version` | `tests/properties/test_properties.py` (schema, `needs_review`, provenance) | [x] |
| AC14 | Determinism (I4) | **Given** the same input twice **when** reviewed **then** the JSON output is identical | `tests/properties/test_properties.py::test_same_input_gives_identical_output` | [x] |
| AC15 | Golden fixture (R8) | **Given** `data/samples/edge_cases.json` **when** reviewed **then** output exactly matches `tests/golden/expected_output.json` | `tests/golden/test_golden.py` | [x] |
| AC16 | CLI errors (R5, I6) | **Given** `[]` / a missing path / invalid JSON **when** the CLI runs **then** exit 0 + message / exit 2 / exit 2, no traceback | `tests/unit/test_cli.py` | [x] |
| AC17 | A-001 AI stub (6, R9) | **Given** a vague description **when** reviewed **then** A-001 with confidence ≤ 0.6 and source `ai_assisted_candidate`; only allowlisted fields reach the suggester; invalid suggester output → no candidate | `tests/unit/test_ai_guardrails.py` | [x] |
| AC18 | Steward decisions (brief: approve/reject/investigate) | **Given** a review file and a decisions file **when** `apply-decisions` runs **then** each valid decision becomes an audit entry with `change_applied: false`; unknown ids and invalid decisions go to `errors`; inputs are unchanged and never overwritten | `tests/unit/test_review.py` | [x] |
| AC19 | AI input gating (discussion 2) | **Given** a row that fails R-001, or has an email, URL or international phone number in an allowlisted field **when** reviewed with `--suggest` **then** nothing from that row reaches the suggester; the prompt builder keeps record text inside one escaped data block | `tests/unit/test_ai_privacy.py` | [x] |
| AC20 | AI eval gate (discussion 3) | **Given** the 12 cases in `data/eval/suggester_cases.json` **when** the stub is evaluated **then** accuracy is 1.0 with no false suggestions, provider errors or empty set, and a worse suggester fails the gate | `tests/unit/test_ai_eval.py` | [x] |
| AC21 | Layer labelling (discussion 6) | **Given** the edge-case file with `--suggest` **when** reviewed **then** every `R-` finding is `deterministic_rule`, every `H-` is `heuristic`, every `A-` is `ai_assisted_candidate`, and rules and heuristics do not import `dq.ai` | `tests/properties/test_layers.py`, `tests/unit/test_architecture.py` | [x] |
| AC22 | Red-zone hook (discussion 4, 8) | **Given** a red-zone path in a Windows absolute form **when** the guard hook runs **then** it blocks (exit 2) | `tests/unit/test_guard_hook.py` | [ ] strict xfail: hook fails open, human patch needed (DECISIONS #26) |

## Edge cases covered (from the brief)
| Edge case | Where |
|---|---|
| Empty input file | AC16 |
| Missing required fields | AC1 |
| Blank strings with whitespace | AC1, AC3 (normalize) |
| Null values | AC3 |
| Duplicate `item_id` | AC5 |
| Same item from different source systems | AC8 |
| Same MPN in different formats | AC8 (canonical MPN) |
| Very short descriptions ("bearing", "valve") | AC7 |
| Useful attributes but wrong category | AC9 |
| Unsupported unit of measure | AC6 |
| Conflicting source-system values | AC5 (conflicting → high) |
| Non-English / abbreviation-heavy | Tokeniser is Unicode-safe; no expansion — **known limitation** (DECISIONS #13) |

## MoSCoW (90 min agent time; Must ≈ 60 min)
- **Must:** JSON ingest + frozen models + normalize; R-001, R-002, R-003, R-004; H-001, H-002 (MPN), H-003; scoring; pipeline with stable sort; CLI + JSON report + markdown summary; property tests (AC11–AC14); golden fixture; `make demo`.
- **Should:** A-001 via `Suggester` Protocol + `StubSuggester` + guardrails (allowlist, schema validation, confidence cap 0.6). Built after the box with the extra human time, opt-in via `--suggest` (DECISIONS #20), together with row gating, a prompt builder and an offline eval gate (DECISIONS #24, #25).
- **Could:** CSV ingest; description-similarity duplicates; FastAPI `POST /review`. (`review.py` decision → audit log was built afterwards with the extra time, DECISIONS #22.)
- **Won't:** real LLM/network, DB, UI, auto-apply of suggestions, translation, auth.

## Slices
| # | Slice | Budget | Proves |
|---|---|---|---|
| S1 | Skeleton: pyproject, config, frozen models, normalize, JSON ingest, R-001 | 15 min | AC1, AC2 + normalize unit tests |
| S2 | Pipeline + CLI: scoring, pipeline, R-002, CLI + JSON report, property tests | 15 min | AC3, AC4, AC11–AC14, AC16 |
| S3 | R-003 duplicate id, R-004 UoM | 10 min | AC5, AC6 |
| S4 | H-001, H-002 (MPN), H-003 + keyword config | 12 min | AC7–AC10 |
| S5 | Samples, edge-case fixture, markdown report, golden test, `make demo` | 8 min | AC15 |
| S6 | *(Should)* AI stub + guardrails, A-001 | 10 min planned; built after the box | AC17 |
| extra | Audit log, eval gate, AI input gating, quality gates (built after the box with the extra human time) | not budgeted | AC18-AC22 |
