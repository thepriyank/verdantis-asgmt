## What & why
<!-- one paragraph; link SPEC requirement IDs (R1, R2…) -->

## Zones touched (docs/AGENT_POLICY.md)
- [ ] 🟢 Green only
- [ ] 🟡 Amber — files + reason + before/after test/eval results:
- [ ] 🔴 Red — must be zero for agent-authored changes

## Red-team (/redteam)
| Severity | Finding | Fix |
|---|---|---|
Mutations survived: N/M

## Checklist
- [ ] `make check` green
- [ ] Tests assert real values incl. edge cases
- [ ] No secrets; AI layer uses field allowlist, validates output, caps confidence
- [ ] Input never mutated; every finding `needs_review` with source + explanation; no "fixed/corrected/auto-approved" wording
- [ ] README / SPEC / AI_USAGE updated
- [ ] I (human) read the full diff
