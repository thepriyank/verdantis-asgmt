# AI usage log

How AI coding tools were used to build this, slice by slice. This answers the brief's questions:
what I asked the AI to do, why I delegated it, how I verified it, what I rejected or changed, and the risks I see.

**Tool:** Claude Code, steered by `CLAUDE.md` (standards), `docs/AGENT_POLICY.md` (what the agent may change), slash commands (`/kickoff`, `/slice`, `/redteam`, `/review`, `/ship`) and subagents (`test-writer`, `red-teamer`, `reviewer`, `docs-writer`, `domain-expert`).

| Time | Slice / step | What I asked the AI | Why delegate | How I verified | What I rejected / changed |
|------|--------------|---------------------|--------------|----------------|---------------------------|
| T+25 | S1 skeleton + R-001 | Models, normalize, ingest, R-001 first draft and tests | Boilerplate-heavy, well specified by SPEC AC1/AC2 | 48 tests, mypy strict, ruff clean; 2 mutations (flip item_id branch, disable parse_error branch) each broke tests | `ruff format .` had reformatted red-zone `.claude/hooks/guard.py`: reverted it and excluded `.claude` in ruff config |
| T+40 | S2 pipeline, R-002, CLI, report, property tests | Tests first (R-002, pipeline, CLI, 4 safety properties), then pipeline/CLI/report/R-002 | Mechanical wiring against clear ACs | 76 tests pass, 98% coverage, mypy strict; mutations (invert MPN test, reverse severity sort) each failed tests; dropping deepcopy in ingest survived because pydantic already copies the dict (equivalent mutant) | Source-scan test caught the word 'Fixed' in a models.py comment: I reworded the comment, not the test |
| T+50 | S3 R-003 duplicate id, R-004 UoM | R-003/R-004 tests and rules; UoM allowlist + alias table in config | Well-specified rules with edge cases listed in SPEC | 100 tests, mypy strict; 4 mutations (group size, provenance in compare, case handling, alias severity key) each failed tests. Tests and code were written together, not red-first. | Treated blank variants as equal in the conflict comparison; alias list is my assumption, needs steward sign-off |
| T+62 | S4 H-001, H-002, H-003 + brief-example test | Heuristic modules, tests, config (generic nouns, category keywords) | Judgement-heavy checks need explicit edge cases; AI drafts, I set the policy (what is vague, ambiguous keywords are skipped) | 138 tests, mypy strict; 5 mutations (digit attribute test, distinct-id guard, ambiguity guard, casefold compare, MPN canonicalisation) each failed tests | Chose to skip category hits whose keywords point to different categories rather than guess; generic-noun and keyword lists are starter vocabularies |
| T+95 | Red-team of S1-S4 (red-teamer agent) | Hunt hallucinated logic, weak tests, unsafe behaviour; 41 mutations | Independent adversarial pass catches what the author misses | Agent found 0 blockers, 3 majors, ~8 minors; 7/41 mutations survived (5 real, 2 equivalent). I fixed all 3 majors, NaN, evidence aliasing and the 5 real survivors with regression tests; re-mutated each fix, 5/5 killed. 153 tests. | The code I generated crashed on deeply nested JSON, let `-o` overwrite the input, and assumed one category taxonomy: all caught by the agent, not by my tests. Left as documented limits: fuzzy manufacturer matching (#6), fields hidden after a malformed row (#18) |
| after box | S6 A-001 AI stub + guardrails (opt-in `--suggest`) | Suggester Protocol, allowlist, response validation, capped confidence, stub, tests | Safe-AI design is a brief requirement; the stub proves the guardrails with a spy suggester | 180 tests, mypy strict; 6 mutations (cap in guardrails, cap in scoring, strict schema, exception handling, malformed-row skip): 5 killed, 1 survived by design (double clamp, DECISIONS #21). Golden file unchanged because A-001 is opt-in | Made the AI layer opt-in rather than default so the human-reviewed golden output stays valid |
| after box | Gaps found reviewing DISCUSSION_NOTES: audit log (`dq/review.py`), coverage floor, CODEOWNERS, secret-scan test | Built what the written answers claimed but the repo lacked | I would rather make the claim true than reword it | 204 tests, mypy strict. A mutation on the decision validation SURVIVED because my parametrised bad-decision cases all used an unknown finding_id, so they failed for the wrong reason; fixed by using a real id, then it was killed. One remaining survivor (dropping `strict=True`) is equivalent | `ci.yml` and branch protection are human-only; the scan runs as a pytest test instead |
| after box | Offline eval harness for the suggester (`dq/ai/evaluate.py`, 12 cases, `eval-suggester`) | Built what DISCUSSION_NOTES #3 claimed | Same reason as the audit log: make the claim true | 217 tests, mypy strict. Three gate mutations SURVIVED at first: at accuracy floor 1.0 the false-suggestion, error and empty-set guards are redundant, so tests could not tell them apart. Added tests with a relaxed floor; all three now killed. Also found the old #3 claimed a rule-contradiction check that does not exist, so I removed that claim | Cases are my own, not steward-labelled |

## What I did NOT delegate
- Product behaviour: what counts as an issue, severity policy, banned language, "never mutate" rule.
- Thresholds and the golden expected output (red-zone; reviewed by me line by line).
- Final review and merge of every change.

## Risks I see in the AI-generated code

Self-critique written after the build. Grouped by how much I would worry.

**Process (how it was built)**
- **Not strictly test-first.** S1 code was written before its tests, and S3 and S6 tests and code were written together. The failing-test step in CLAUDE.md §1.4 was skipped there; mutation checks were the compensation, not a substitute.
- **Same author for code and tests.** The AI wrote both, so they share blind spots. The independent red-team found three majors my tests missed (crash on nested JSON, `-o` overwriting the input, a taxonomy assumption). That is evidence the next unknown defect is probably still there.
- **I over-claimed once.** The README said 100% coverage of `dq/ai`; the real figure was 94% for `stub.py`. Caught on the self-review, not by a check. Numbers in docs are typed by hand and can drift from reality; there is no CI step that regenerates them.
- **Time overrun and approximate logs.** The build ran past the 90-minute agent budget, and the clock times in the prompt log and AI_USAGE rows are rounded estimates, not recorded timestamps.
- **Never run in CI or on Windows `make`.** `make` is not installed in the build shell, so `make check` and `make demo` were never run as written; I ran the underlying `uv` commands. The GitHub workflow has never executed. Line-ending warnings (LF/CRLF) appeared on every commit.

**Product judgement baked into code (needs a steward, not a developer)**
- **Every threshold and word list is my guess:** confidence values (0.95, 0.9, 0.85, 0.7, 0.6), severities, the UoM allowlist and alias table (for example "unit" -> EA, "pair" -> PR), the generic-noun list, and the category keywords. None were calibrated against real steward decisions, so confidence is a label, not a probability.
- **H-003 is the noisiest check.** Whole-word keyword matching with a three-category taxonomy: a valve filed under Mechanical, a "terminal" that is a pipe fitting, or "seal"/"chain" in another sense will be flagged. It is low severity and low confidence, but a steward will still read each one. English only.
- **R-003 assumes `item_id` is unique across all source systems.** If systems legitimately share id ranges, it will be loud (high severity for conflicting rows).
- **H-002 trusts exact manufacturer text.** "SKF", "SKF Inc." and "S K F" do not match, so real duplicates are missed (false negatives are silent). Kits and revisions that share a part number would be false positives.
- **A malformed row hides its other problems** until it is resent (DECISIONS #18).
- **The golden file locks today's behaviour, including its mistakes.** It was generated by the code under test and then reviewed by a human; a snapshot test is only as good as that review, and any config tuning forces a regeneration.

**Engineering**
- **Tests are coupled to config values** (for example `0.85`, `0.95`), so retuning a threshold breaks tests that are really checking policy. Several test helpers use `# type: ignore[no-untyped-def]`.
- **The AI layer is only proven against my own stub and a spy.** I have not seen how a real provider fails (slow, partial JSON, injected instructions inside a description). The broad `except Exception` in `a001_suggestion.py` is deliberate but would also hide programming errors; it logs a warning only. The double confidence clamp has one mutation that survives by design.
- **No performance or size testing.** The whole file is read into memory and H-002 groups in one pass; fine for uploads of thousands of rows, untested beyond a few dozen.
- **Unused dependency surface.** `pyproject.toml` declares an optional `api` extra (FastAPI, uvicorn) with no code behind it, which the lock file also carries. It is excluded from `make setup`, but it is a dependency added without a feature.
- **Blast radius of formatters and hooks.** Early on `ruff format .` rewrote a red-zone hook file; I reverted it and excluded `.claude` from ruff. A post-write formatter also rewrote several test files after I wrote them, so the committed text differs slightly from what I authored.
- **Manual mutation testing only.** The mutation checks were hand-made one-line edits (about 70 in total, mine and the agent's), not an automated tool run in CI, so coverage of "what a good test suite would catch" is partial.

**What I would do next to reduce these risks:** add `mutmut` or similar to CI for `dq/rules` and `dq/heuristics`; label a sample of real records with a steward and measure precision per rule; replace config-value assertions with policy-level tests; exercise the suggester against a recorded real-provider transcript including hostile descriptions; and run `make check` on a Linux CI runner before submitting.
