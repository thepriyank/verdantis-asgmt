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

## What I did NOT delegate
- Product behaviour: what counts as an issue, severity policy, banned language, "never mutate" rule.
- Thresholds and the golden expected output (red-zone; reviewed by me line by line).
- Final review and merge of every change.

## Risks I see in the AI-generated code
-
