---
description: Independent review of the repo against CLAUDE.md before submission
---
Use the `reviewer` subagent to review the current repo against CLAUDE.md §5–§10 and docs/SPEC.md.
Then run the `red-teamer` subagent on the full diff from the first commit, and the `security-auditor` subagent for secrets, injection and unsafe input handling.
Merge both into one list ranked by: (1) breaks running/demo, (2) wrong domain logic, (3) missing test, (4) style.
Fix category 1–2 items now. List the rest under "Known limitations" in README. $ARGUMENTS
