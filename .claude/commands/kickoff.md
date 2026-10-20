---
description: Turn the pasted assignment into SPEC.md, a scoped plan and a task list (no code yet)
---
Read CLAUDE.md and docs/ASSIGNMENT.md fully. Then, WITHOUT writing any app code:

1. Summarise the brief in 5 bullets: problem, users, inputs, outputs, constraints.
2. List every explicit requirement (R1, R2…) and every implicit one a reviewer will expect (tests, README, one-command run).
3. List ambiguities. For each, pick the simplest reasonable assumption and log it in docs/DECISIONS.md.
4. Scope with MoSCoW for a 3-hour box (build time ≈ 110 min). Must-haves must fit in 90 min.
5. Write docs/SPEC.md: goal, non-goals, data model, API/CLI surface, acceptance criteria per requirement (Given/When/Then).
6. Break the Must-haves into 4–6 vertical slices, each ≤ 25 min, with the test that proves it.
7. Write docs/ARCHITECTURE.md with a Mermaid diagram.
8. Stop and show me the slice list for approval. $ARGUMENTS
