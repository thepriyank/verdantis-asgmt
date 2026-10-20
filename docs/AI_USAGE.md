# AI usage log

How AI coding tools were used to build this, slice by slice. This answers the brief's questions:
what I asked the AI to do, why I delegated it, how I verified it, what I rejected or changed, and the risks I see.

**Tool:** Claude Code, steered by `CLAUDE.md` (standards), `docs/AGENT_POLICY.md` (what the agent may change), slash commands (`/kickoff`, `/slice`, `/redteam`, `/review`, `/ship`) and subagents (`test-writer`, `red-teamer`, `reviewer`, `docs-writer`, `domain-expert`).

| Time | Slice / step | What I asked the AI | Why delegate | How I verified | What I rejected / changed |
|------|--------------|---------------------|--------------|----------------|---------------------------|

## What I did NOT delegate
- Product behaviour: what counts as an issue, severity policy, banned language, "never mutate" rule.
- Thresholds and the golden expected output (red-zone; reviewed by me line by line).
- Final review and merge of every change.

## Risks I see in the AI-generated code
-
