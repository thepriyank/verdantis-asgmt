# Agent Policy — how AI coding agents work in this repo

**Principle:** agents speed up delivery; humans own correctness. Every change is reviewed by a person, and the riskier the file, the stronger the gate. In the 2-hour assignment box there was no pull-request flow (DECISIONS #0): each slice was committed to `main` by the agent after the checks were green, and the human reviewed the work slice by slice in the session and read the full diff before submission.

## Zones

| Zone | What | Agent | Human gate |
|---|---|---|---|
| 🟢 Green | CLI, pipeline wiring, report formatting, docs, README, sample data | Create/edit/refactor | Diff review |
| 🟡 Amber | Rules, heuristics, scoring policy, AI guardrails, config thresholds, tests, dependencies | Edit with written reason + before/after test results (recorded in `docs/AI_USAGE.md` and `docs/DECISIONS.md`); may add tests, never delete or loosen them | Explicit approval per slice |
| 🔴 Red | CLAUDE.md, `.claude/`, this policy, CI workflows, `.env*`, the golden expected output | Propose only | Human edits, or gives explicit one-time permission in chat |

## How the red zone is protected (and where it is not)

- `.claude/hooks/guard.py` blocks agent edits to red-zone paths given as relative or POSIX-absolute paths. **It fails open on Windows absolute paths** (`C:\...`), so it did not block anything on the build machine. This is documented by strict-xfail tests in `tests/unit/test_guard_hook.py` and tracked as DECISIONS #26. Until a human patches the hook, the real protection is this policy, the agent's instructions and human review of the diff.
- `.claude/settings.json` has `deny` rules for the golden file and the CI workflows. They have not been verified on Windows.
- `.github/CODEOWNERS` routes red-zone paths to the owner. It only takes effect once branch protection requires code-owner review on GitHub; that setting is not enabled.
- The golden expected output is never written by an agent. The agent proposes it (in `out/`) and the human reviews and places it.

**Red-zone exceptions during this build** (each needed an explicit instruction from the human in chat):
1. `CLAUDE.md`: one-time permission to change the time box from 3 h to 2 h and replace the PR flow with commits to `main`.
2. `docs/AGENT_POLICY.md` (this file): updated at the human's request to match what was actually done.
3. `tests/golden/expected_output.json` and `.env.example` were created by the human, not the agent.

## Review gates (every change)

1. Checks green before each commit: `ruff check`, `ruff format --check`, `mypy` (strict on `dq/`) and `pytest` with the 95% coverage floor. The same checks are in `.github/workflows/ci.yml`, which has not yet run on GitHub.
2. `/redteam` on risky changes: it was run once over slices S1 to S4, with findings, fixes and "mutations survived N/M" recorded in `docs/AI_USAGE.md` (there were no pull-request bodies). Later work was checked with hand-made mutations.
3. The human reads the diff. The pull-request template checklist is the intended list for a team setting.
4. Amber files carry a reason and evidence in `docs/AI_USAGE.md` or `docs/DECISIONS.md`. Red files are changed only by the human or with explicit permission, as logged above.

## Product-side rule (the assistant we ship)

Mirrors MRO360's "agents propose, humans approve" model: the assistant only emits review candidates with `status: needs_review`. Nothing is auto-applied. Steward decisions are recorded by `python -m dq apply-decisions` in an append-only audit log, with `change_applied` always false. A future auto-apply path would additionally need: a confidence threshold per rule, a per-rule kill switch, and a steward override rate tracked as a quality metric (the audit log is the data source for the last one).

## Rolling this out to a team

- Week 1: adopt CLAUDE.md and the zones; make the red-team checklist mandatory on pull requests; fix the guard hook so it works on every platform the team uses, and turn on branch protection with code-owner review.
- Week 2: track agent-authored change stats (review time, defects found after merge, surviving mutations).
- Ongoing: every bug found in AI code becomes a new red-team rule or a test; prune rules nobody needs. This build's example: the independent red-team found three real defects the author's own tests missed (DECISIONS #17 to #19), and testing the guard hook found it failing open (DECISIONS #26).
