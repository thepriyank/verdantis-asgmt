# Claude Code prompt playbook

The exact prompts used to build this, in order. Committed on purpose: it shows reviewers *what I asked the AI to do*.
Clock times assume a 3:00 time box. **Bold = what I (the human) do myself.**

---

## 0:00 — Setup (human, ~5 min, before starting Claude)

```bash
gh repo create verdantis-item-dq-assistant --private --clone
cd verdantis-item-dq-assistant
# unzip verdantis-claude-kit.zip here, then move the contents of verdantis-kit/ (incl. hidden .claude and .github) to the repo root
mv README.template.md README.md
git add -A && git commit -m "chore: project standards, agent policy and brief"
git push -u origin main
claude
```

Fill in "Received / Deadline" at the top of `docs/ASSIGNMENT.md` yourself.

---

## 0:05 — Prompt 1 · Kickoff (switch to Plan Mode with Shift+Tab first)

```
/kickoff

Read CLAUDE.md and docs/ASSIGNMENT.md completely before answering. Do not write any code in this step.

Context: this is a 3-hour interview exercise. Reviewers care more about HOW we build (planning, delegation, verification, safety, trade-offs) than about how much we build. CLAUDE.md §4 already proposes a check catalogue and §5 an output schema — challenge them if the brief suggests something better, otherwise adopt them.

Produce:
1. A 6-bullet summary of the brief: input, output, required behaviour, what must stay human-controlled, what is deterministic, what could be AI-assisted.
2. A requirement list mapped to the brief's 9 functional checks, with my proposed scope:
   - MUST: #1 missing MPN, #2 vague description, #3 possible duplicates (duplicate item_id + same manufacturer/canonical MPN across systems + high description similarity), #5 unsupported UoM, #7 malformed/incomplete rows, #8 severity + confidence, #9 explanation per finding.
   - SHOULD: #4 category mismatch (keyword heuristic), #6 normalized description suggestion via a stubbed AI suggester with guardrails.
   - COULD: apply a human decisions file (approve/reject/investigate) → audit log without touching originals; a FastAPI POST /review wrapper.
   - WON'T: real LLM calls, database, UI, auth.
   Tell me if this scope is unrealistic for ~110 minutes of build time.
3. Every edge case from the brief's "Edge Cases to Consider" list, each mapped to the check and test that will cover it. Flag any we will knowingly not cover.
4. Ambiguities in the brief. For each, propose the simplest reasonable assumption. Write them to docs/DECISIONS.md (number, decision, options, why, trade-off). Include at least: what counts as "required" fields; UoM allowlist; what "vague" means; duplicate similarity threshold; how to treat the same item_id from different source systems; whether CSV is in scope.
5. Fill docs/SPEC.md: goal, non-goals, input/output contract, requirements table with Given/When/Then acceptance criteria and the test name that proves each, MoSCoW.
6. Fill docs/ARCHITECTURE.md (keep the existing Mermaid, adjust if needed) and add 3 short paragraphs: data flow; where a real LLM plugs in and its safeguards; why each check is a rule, a heuristic, or AI.
7. A slice plan: 5–6 vertical slices, each ≤ 20 minutes, each with the files it touches, the tests it adds, and its zone (green/amber) from CLAUDE.md §12.
8. A risk list: what could go wrong in the build and the fallback.

Stop after this and wait for my approval. Do not scaffold yet.
```

**Human (0:15–0:20):** read the plan critically. Change at least one thing that you would do differently (e.g. a threshold, a scope cut, an assumption) and say why — this is your evidence of judgment. Then log it in AI_USAGE.md (next prompt does that).

```
Changes to your plan: <your edits, e.g. "duplicate text similarity threshold 0.85 not 0.8 — at 0.8 'bearing' and 'bearing housing' would match; add a test for that pair">.
Apply them to SPEC.md and DECISIONS.md. Then add the first row to docs/AI_USAGE.md: "Kickoff — asked Claude to decompose the brief into spec, assumptions and slices; delegated because it is fast at enumerating requirements and edge cases; I verified every requirement against the brief; I changed: <what you changed>".
Commit as "docs: spec, assumptions and slice plan".
```

---

## 0:20 — Prompt 2 · Scaffold

```
Exit plan mode. Scaffold the project exactly as CLAUDE.md §2 and §3 describe:
- pyproject.toml managed by uv (python 3.12; deps: pydantic>=2; dev deps: pytest, pytest-cov, ruff, mypy). No other dependencies without asking me.
- Empty package structure under dq/ with __init__.py files and a `dq/__main__.py` that calls cli.main.
- config/rules.json with the thresholds, severity map, UoM allowlist + aliases, required fields and banned words agreed in SPEC/DECISIONS. config/category_keywords.json with a small, documented keyword map.
- tests/ folders with one smoke test that imports dq.
- ruff + mypy config in pyproject (mypy strict for dq/).
Run `make setup` and `make check`; show me the output. Commit "chore: scaffold project". Then push and tell me when CI runs.
```

**Human:** confirm CI is green on GitHub.

---

## 0:30 — Prompt 3 · Slice 1: models, ingest, normalize, malformed rows (R-001) + safety property tests

```
/slice models-ingest-normalize

Scope:
- dq/models.py: RawRecord (frozen, keeps original values exactly as received, including unknown extra fields), ParsedRecord (frozen; row_index; original + read-only normalized views), ReviewCandidate exactly matching CLAUDE.md §5, enums for Severity, Source, IssueType, Status (only "needs_review"), AllowedAction.
- dq/normalize.py: pure functions — is_missing() per CLAUDE.md §4 blank handling, clean_text(), canonical_mpn(), canonical_uom() using config aliases, tokenize().
- dq/ingest.py: load JSON (list of objects) and CSV; never raise on a bad row — produce parse issues instead; empty file / empty list → zero records and a clear message; unreadable file → a typed error the CLI maps to exit code 2.
- dq/rules/malformed_row.py (R-001): missing required fields, wrong types (e.g. item_id as list), non-object rows.
- dq/scoring.py: one place for severity + confidence per rule_id, read from config.

Tests first (use the test-writer subagent to draft them, then show me the list before implementing):
- normalize: None, "", "   ", "null", "N/A", "-" → missing; "6205-ZZ" / "6205 zz" / "6205ZZ" / "6205.zz" → same canonical MPN; "each"/"Each "/"EA" → "EA".
- ingest: empty list, empty file, non-list JSON, a row that is a string, CSV with missing columns, unknown extra fields preserved.
- R-001: missing item_id → high; missing description → medium; wrong type → medium; evidence contains the original values.
- tests/properties/test_no_mutation.py: deep-copy input, run ingest + R-001, assert input unchanged.
- tests/properties/test_schema.py: every candidate validates and has status "needs_review" and allowed_actions.

Keep functions small. Run make check, show output, update SPEC ticks, add an AI_USAGE row, commit.
```

**Human verify:** read `normalize.py` line by line — it is the base of every match. Try one input yourself in a Python shell.

---

## 0:50 — Prompt 4 · Slice 2: missing MPN (R-002) and unit of measure (R-004)

```
/slice rules-mpn-uom

- dq/rules/missing_mpn.py (R-002): manufacturer present AND MPN missing (per is_missing) → candidate. If manufacturer is also missing, do NOT raise R-002 (R-001 or nothing covers it — follow DECISIONS.md). Explanation and suggested action wording like the brief's example output.
- dq/rules/unit_of_measure.py (R-004): missing UoM → covered by R-001 only if required, else low; known alias (EACH, PCS, Pc) → low, suggested_value = canonical code, action "Review proposed UoM code before approval"; unknown value (e.g. "BX12", "??", "1") → medium, "Confirm the unit of measure with the source owner".
- Wording must use "candidate", "suggested", "needs review" — never "fixed"/"corrected".

Tests first: positive, negative, whitespace-only MPN, manufacturer missing, lowercase alias, unknown code, numeric UoM. Add tests/properties/test_language.py that scans every explanation/suggested_action produced by ALL registered checks for banned words from config.
make check, AI_USAGE row, commit.
```

---

## 1:10 — Prompt 5 · Slice 3: duplicates (R-003, H-002) and vague descriptions (H-001)

```
/slice duplicates-and-vague

- dq/rules/duplicate_item_id.py (R-003): same item_id appearing more than once. Same item_id + same source_system → high ("duplicate key"). Same item_id in different source systems → do not assume a duplicate; raise only if key attributes conflict, as agreed in DECISIONS.md. related_item_ids / record_refs list all rows involved.
- dq/heuristics/potential_duplicate.py (H-002): (a) same canonical manufacturer + same canonical MPN across different rows/systems → medium, confidence 0.9, evidence shows both raw MPNs; (b) description similarity using difflib ratio on normalized tokens ≥ threshold from config AND same manufacturer (or manufacturer missing) → confidence scaled 0.6–0.8. Emit ONE candidate per duplicate group, not one per pair, and make group ordering deterministic. Keep it O(n²) but document the limit (fine for upload sizes in this slice; blocking by manufacturer is the next step).
- dq/heuristics/vague_description.py (H-001): missing → leave to R-001; ≤ 2 tokens or only generic nouns from config ("bearing", "valve", "pump", "part", "item", "misc") and no attribute token (digits, size units, MPN-like token) → candidate. "bearing" → medium; "SKF Bearing 6205 ZZ" → no finding. Abbreviation-heavy text ("BRG BALL 6205") must NOT be flagged as vague just because it is short — it has attributes.

Use the domain-expert subagent to sanity-check thresholds and the generic-noun list before implementing, and tell me what it recommended.
Tests first, including: "6205-ZZ" vs "6205 zz" from ERP-A and ERP-B → one potential duplicate; "bearing" vs "bearing housing" → NOT duplicate at the agreed threshold; three-way duplicate → one group; duplicate item_id same system vs. different systems; very short non-English description (e.g. "rodamiento") → vague, low confidence.
make check, AI_USAGE row, commit.
```

**Human verify:** run the duplicate test pairs yourself and decide if the threshold feels right. Log what you changed.

---

## 1:30 — Prompt 6 · Slice 4: pipeline, CLI, report, sample data, golden test

```
/slice pipeline-cli-golden

- dq/pipeline.py: registry of checks (rules first, then heuristics, then AI); run all; collect candidates + parse issues; stable sort (severity desc, item_id, rule_id); deterministic finding_id (hash of rule_id + record refs). Must never mutate input.
- dq/report.py: JSON output {summary, candidates, parse_issues}; markdown report for a steward: counts by severity/source, then a table per issue type with item, explanation, suggested action.
- dq/cli.py: `python -m dq review <path> [-o out.json] [--report out.md]`; exit 0 on success (including "no records"), 2 on unreadable input; never prints a stack trace for user errors.
- data/samples/sample_input.json: ~15 realistic records across ERP-A / ERP-B / ERP-C, including the brief's two examples.
- data/samples/edge_cases.json: one record per edge case in the brief's list; data/samples/sample_input.csv mirroring a few rows.
- tests/properties/test_determinism.py: same input twice → byte-identical JSON.
- Golden test: generate tests/golden/expected_output.json with `make golden` — but DO NOT write that file yourself (it is red-zone). Show me the output; I will review it and run `make golden` myself.
make check and make demo; paste the markdown report; commit.
```

**Human:** read every finding in the golden output. Remove/adjust anything noisy (false positives) by changing config or code — not the golden file. Then run `make golden` yourself and commit `test: golden output reviewed by human`.

---

## 1:50 — Prompt 7 · Slice 5 (Should): category mismatch (H-003) + stub AI suggester (A-001)

```
/slice category-and-ai-stub

- dq/heuristics/category_mismatch.py (H-003): keyword map from config → expected category; if the description strongly implies a different category than the record's category → low severity, confidence 0.5–0.75 by keyword strength, source "heuristic". Example: "SKF Bearing 6205 ZZ" with category "Electrical" → candidate; explanation names the keyword.
- dq/ai/: Suggester Protocol; StubSuggester (deterministic: expands abbreviations from a small map, orders tokens as NOUN, MODIFIER, attributes, uppercase); guardrails.py:
  - build_request(): field ALLOWLIST only (item_description, manufacturer, category, unit_of_measure); record text wrapped as data.
  - validate_response(): Pydantic schema, reject unknown fields, require explanation, clamp confidence to config cap (0.6), drop a suggestion identical to the original or one that contradicts a deterministic finding.
  - A-001 normalized description suggestion: source "ai_assisted_candidate", suggested_value = proposed description, action "Review suggested description before approval".
- Add a docstring in dq/ai/__init__.py describing how AnthropicSuggester would plug in later (timeouts, retries, PII filtering, cost/latency logging, eval set, kill switch) — no code for it.
Tests: allowlist test (a record with an extra "notes" or "price" field never reaches the suggester); confidence cap; invalid AI response → no candidate and no crash; category mismatch positive/negative.
make check, AI_USAGE row, commit.
```

If behind schedule at 1:50: skip this slice and the next; write them under "Next steps".

---

## 2:10 — Prompt 8 · (Could) human decisions → audit log

```
/slice review-decisions

dq/review.py + CLI subcommand `python -m dq apply-decisions out/review.json decisions.json -o out/audit.json`:
decisions.json = [{finding_id, decision: approve|reject|investigate, reviewer, note}].
Output an audit log (finding, decision, reviewer, timestamp passed in, before value, suggested value). It must NOT modify the input records file; "approve" only records intent for a downstream system. Tests: unknown finding_id → error entry, not crash; originals unchanged.
make check, commit.
```

---

## 2:20 — Prompt 9 · Red-team and review

```
/redteam
```
then
```
/review
```

**Human:** read the findings. Fix blockers. For at least one finding, decide *not* to fix it and record why in DECISIONS.md (trade-off evidence). Make sure AI_USAGE.md lists at least 3 concrete things you rejected or changed from AI output during the build.

---

## 2:35 — Prompt 10 · Docs (draft by AI, edited by you)

```
Use the docs-writer subagent to fill README.md from the template using REAL output from `make demo` and `make check` (run them; never invent output). Then draft docs/DISCUSSION_NOTES.md: 3–4 bullet answers to each of the 8 discussion topics, each tied to a concrete file or test in this repo. Draft the "Risks I see in the AI-generated code" section of AI_USAGE.md. Keep everything short and plain.
```

**Human:** rewrite DISCUSSION_NOTES and the README "Status" section in your own words — you will be asked these live.

---

## 2:45 — Prompt 11 · Ship (code freeze)

```
/ship
```

**Human:** approve the push, add the reviewer as collaborator (`gh repo edit --visibility public` or `gh api repos/<you>/<repo>/collaborators/<their-username> -X PUT`), send the email.

---

## Recovery prompts (use when needed)

- Going off-plan: `Stop. Revert uncommitted changes with git restore. Re-read CLAUDE.md §1 and the current slice in SPEC.md, then redo only <X> touching only <files>.`
- A test was weakened: `You changed an assertion in <test>. That is not allowed (CLAUDE.md §1.4). Restore the original assertion and fix the implementation instead.`
- Too much code: `This is more code than the slice needs. Show me the smallest change that meets the acceptance criteria.`
- Unsure about AI output: `Explain this function line by line and give me two inputs where it would give a wrong answer.`
