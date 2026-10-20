---
description: Red-team the current branch's AI-generated changes before merge
---
Use the `red-teamer` subagent on `git diff main...HEAD` (or on $ARGUMENTS if given).
Then:
1. Fix every blocker and major finding (respecting docs/AGENT_POLICY.md zones).
2. Re-run `make check` and the mutation check for anything you changed.
3. Write a "Red-team" section for the PR body: findings, fixes, mutations survived N/M.
4. Add one line to docs/AI_USAGE.md: what the agent got wrong and how it was caught.
