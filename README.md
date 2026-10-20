# Item Data-Quality Assistant — review candidates for a human data steward

> Verdantis Agentic Coding Lead assignment · built in a 3-hour time box with Claude Code.

## What it does
Reads item master records (JSON/CSV) from several source systems and produces **review candidates** — structured, explainable findings a data steward can approve, reject or investigate. It **never modifies the records**.

## Run it
```
make setup
make demo        # sample input → out/review.json + out/review.md
make check       # lint + types + tests
python -m dq review <your-file.json|csv> -o out.json --report out.md
```

## Sample input → output
<short input snippet> → <short output snippet>

## Checks implemented
| Brief # | Check | Source | Status |
|---|---|---|---|

## Design
- Deterministic rules vs. heuristics vs. AI-assisted (stub) — separated by module and labelled on every finding
- Input is frozen; property test proves no mutation
- Output contract: see CLAUDE.md §5 · Architecture: docs/ARCHITECTURE.md

## Tests and verification
<counts, coverage, golden test, property tests, how to run>

## Assumptions & trade-offs
See docs/DECISIONS.md (top items here).

## How I used AI
Summary + docs/AI_USAGE.md · guardrails in CLAUDE.md and docs/AGENT_POLICY.md.

## Status
- **Works now:**
- **Incomplete:**
- **Risks:**
- **Next steps:**
