# AI usage log

How AI coding tools were used to build this, slice by slice. This answers the brief's questions:
what I asked the AI to do, why I delegated it, how I verified it, what I rejected or changed, and the risks I see.

**Tool:** Claude Code, steered by `CLAUDE.md` (standards), `docs/AGENT_POLICY.md` (what the agent may change), slash commands (`/kickoff`, `/slice`, `/redteam`, `/review`, `/ship`) and subagents (`test-writer`, `red-teamer`, `reviewer`, `docs-writer`, `domain-expert`).

| Time | Slice / step | What I asked the AI | Why delegate | How I verified | What I rejected / changed |
|------|--------------|---------------------|--------------|----------------|---------------------------|
| T+25 | S1 skeleton + R-001 | Models, normalize, ingest, R-001 first draft and tests | Boilerplate-heavy, well specified by SPEC AC1/AC2 | 48 tests, mypy strict, ruff clean; 2 mutations (flip item_id branch, disable parse_error branch) each broke tests | `ruff format .` had reformatted red-zone `.claude/hooks/guard.py`: reverted it and excluded `.claude` in ruff config |
| T+40 | S2 pipeline, R-002, CLI, report, property tests | Tests first (R-002, pipeline, CLI, 4 safety properties), then pipeline/CLI/report/R-002 | Mechanical wiring against clear ACs | 76 tests pass, 98% coverage, mypy strict; mutations (invert MPN test, reverse severity sort) each failed tests; dropping deepcopy in ingest survived because pydantic already copies the dict (equivalent mutant) | Source-scan test caught the word 'Fixed' in a models.py comment: I reworded the comment, not the test |

## What I did NOT delegate
- Product behaviour: what counts as an issue, severity policy, banned language, "never mutate" rule.
- Thresholds and the golden expected output (red-zone; reviewed by me line by line).
- Final review and merge of every change.

## Risks I see in the AI-generated code
-
