---
description: Build one vertical slice test-first, verify, and commit
---
Build slice: $ARGUMENTS

0. Create a branch `feat/<slice-name>` from main.
1. Restate the slice goal and its acceptance criteria from docs/SPEC.md (3 bullets).
2. Write or extend the failing test(s) first. Run them; confirm they fail for the right reason.
3. Implement the minimum code to pass, following CLAUDE.md layout and standards.
4. Run `make check`. Fix until green. Never weaken a test.
5. Update README (feature + example) and tick the criteria in SPEC.md.
6. Append a row to docs/AI_USAGE.md: what was delegated, why, how verified, what I changed/rejected.
7. Commit with a Conventional Commit message.
8. Run /redteam, fix blockers, then `gh pr create` using the PR template (fill the zones touched + red-team section).
9. Show me the PR link, diff summary and `make check` output. I review and merge — never merge yourself.
