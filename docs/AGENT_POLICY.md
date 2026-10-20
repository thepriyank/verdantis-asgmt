# Agent Policy — how AI coding agents work in this repo

**Principle:** agents speed up delivery; humans own correctness. Every change is reviewed by a person before it reaches `main`, and the riskier the file, the stronger the gate.

## Zones

| Zone | What | Agent | Human gate |
|---|---|---|---|
| 🟢 Green | CLI, pipeline wiring, report formatting, docs, README, sample data | Create/edit/refactor | Diff review in PR |
| 🟡 Amber | Rules, heuristics, scoring policy, AI guardrails, config thresholds, tests, dependencies | Edit with written reason + before/after test results; may add tests, never delete or loosen them | Explicit approval per file |
| 🔴 Red | CLAUDE.md, `.claude/`, this policy, CI workflows, `.env*`, the golden expected output | Propose only | Human edits |

Red zone is enforced by `.claude/hooks/guard.py` (blocks the edit) and `.claude/settings.json` deny rules.

## Review gates (every PR)

1. `make check` green in CI.
2. `/redteam` run; findings + "mutations survived N/M" in the PR body.
3. Human reads the full diff; ticks the PR template checklist.
4. Amber files: reason + evidence present. Red files: none changed by the agent.

## Product-side rule (the assistant we ship)

Mirrors MRO360's "agents propose, humans approve" model: the assistant only emits review candidates with `status: needs_review`. Nothing is auto-applied in this slice. A future auto-apply path would need: a confidence threshold per rule, a per-rule kill switch, an audit row per decision, and a steward override rate tracked as a quality metric.

## Rolling this out to a team

- Week 1: adopt CLAUDE.md + zones; red-team checklist mandatory on PRs.
- Week 2: track agent-authored PR stats (review time, defects found after merge, surviving mutations).
- Ongoing: every bug found in AI code → a new red-team rule or a test; prune rules nobody needs.
