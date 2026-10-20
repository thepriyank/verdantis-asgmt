# Claude Code prompt log

The prompts actually used to build this, in the order they were used. Committed on purpose: it shows reviewers *what I asked the AI to do* and how the plan changed.
**Bold = what I (the human) did myself.** The time box was **2 hours**, not the 3 hours the starter kit assumed. Clock times are approximate (elapsed time from the start of the box, rounded); the per-slice budgets are the ones in `docs/SPEC.md`.

| Clock | Step | Budget | Actual (approx.) |
|---|---|---|---|
| 0:00–0:20 | Human setup: repo, kit, reading the brief | — | 20 min before Claude started |
| 0:20–0:30 | Kickoff plan, plan correction, CLAUDE.md timebox edit, docs commit | 5 min | ~10 min (one plan rejected and redone for the 2 h box) |
| 0:30–0:50 | S1 skeleton, ingest, normalize, R-001; scaffold of the remaining layout | 15 min | ~20 min |
| 0:50–1:05 | S2 pipeline, R-002, CLI, reports, property tests | 15 min | ~15 min |
| 1:05–1:15 | S3 R-003, R-004 | 10 min | ~10 min |
| 1:15–1:30 | S4 H-001, H-002, H-003 | 12 min | ~15 min |
| 1:30–1:40 | Red-team of S1–S4 (agent), fixes, regression tests | — | ~10 min |
| 1:40–1:50 | S5 edge-case fixture, golden file (human), README, discussion notes, ship checks | 8 min | ~10 min |
| 1:50–2:00 | **Human: final look and share the link** | 10 min | reserved |
| after | Extra human minutes used for the A-001 suggester (S6) and this log | — | see end |

**Plan changes vs. the starter playbook** (and why): 3 h → 2 h box; no PR per slice (commit to `main` after a green check, logged in DECISIONS #0); CSV ingest, fuzzy-description duplicates and the decisions/audit log cut; A-001 (S6) deferred, then built opt-in with the extra time; red-team moved after S4 instead of the end so its findings could still be fixed.

---

## 0:00 — Setup (human, before starting Claude)

Repo created and the kit copied in. **Filled the brief into `docs/ASSIGNMENT.md` myself.** Started `claude` in the project folder.

---

## 0:20 — Prompt 1 · Kickoff (Plan Mode)

```
/kickoff
```
(the command in `.claude/commands/kickoff.md`: read CLAUDE.md and the brief, summarise it in 5 bullets, list explicit and implicit requirements, list ambiguities with assumptions, MoSCoW for the box, write SPEC.md and ARCHITECTURE.md, break the Must-haves into 4–6 slices, then stop for approval.)

Claude produced a plan. **I rejected it:**
```
You have a mistake, update all references to match this fix. The timeframe is 2 hours not 3 hours. and we have already spent 20 minutes out of it. So fix the plan and timeframes to make sure we complete this in the next 1 hour 40 minutes, keeping 10 minutes for me to take a final look and share the link with them.
```
Claude redid the plan: 90 min of agent work, 10 min human, Must slices S1–S5 = 60 min, S6 only if on schedule. **I approved the plan.** Claude wrote `docs/SPEC.md`, `docs/DECISIONS.md` (17 assumptions) and `docs/ARCHITECTURE.md`, then stopped and showed the slice list.

```
I permit you to update claude.md this one time to fix the timeframe issue and update the PRs flow based on the new timeline.
```
CLAUDE.md is red-zone, so this was an explicit one-time human permission: 3 h → 2 h, slice time-box 5 min, commit to `main` instead of PRs. (I also switched the session model with `/model` here.)

```
approved, commit the docs and start S1
```

---

## 0:30 — Slice 1: models, ingest, normalize, R-001 (+ scaffold)

Started by approval above. Claude built `pyproject.toml`, `config/rules.json`, frozen models, `normalize.py`, `ingest.py`, `scoring.py`, R-001 and 48 tests. It also reformatted a red-zone hook file by accident (`ruff format .`); it reverted that and excluded `.claude` in the ruff config.

```
Check if the steps 2 and 3 defined in Claude.md to scaffold the project are completed
```
Claude compared CLAUDE.md §2 (stack) and §3 (layout) with the repo and listed what was missing.
```
scaffold
```
Docstring-only placeholders for the missing modules and folders.
```
I've already created .env.example in the root. Complete steps 2 and 3 as described in claude.md
```
Added `config/category_keywords.json`, `dq/review.py`, `dq/ai/*` placeholders and the optional `api` extra. **I created `.env.example` myself** (red-zone; CI needs it).
```
/slice models-ingest-normalize
```
I ran this by name; Claude pointed out S1 had already built it, skipped the branch/PR steps (they no longer apply), ticked AC1/AC2 and updated the README.

---

## 0:50 — Slice 2: pipeline, R-002, CLI, reports, property tests

```
yes, start S2
```
Tests first (R-002, pipeline sort and summary, CLI exit codes, four safety properties), confirmed failing, then implementation. Mutation checks on the new code. A source-scan test caught the word "Fixed" in a comment; the comment was reworded, not the test.

---

## 1:05 — Slice 3: R-003 duplicate item_id, R-004 unit of measure

```
continue in order, start S3
```
Decision I made when asked to choose between cutting S3 and continuing: **continue in order.** Rules, UoM allowlist and alias table in config, 4 mutation checks.

---

## 1:15 — Slice 4: H-001, H-002, H-003

```
yes, start S4
```
Heuristics plus the brief-example test. 5 mutation checks. Committed before the red-team to protect the clock.

---

## 1:30 — Red-team

```
/redteam
```
Claude launched the `red-teamer` agent on the S1–S4 range (the diff against `main` is empty when committing to `main`). While it ran I asked for S5:
```
continue with S5
```
Claude built `data/samples/edge_cases.json` and proposed the golden output into `out/` (not into the red-zone file) and staged the golden test. **I reviewed the proposed output and placed `tests/golden/expected_output.json` myself.**
```
I placed the golden file, check the red-team result
```
The agent reported 0 blockers, 3 majors (crash on deeply nested JSON; `-o` overwriting the input; H-003 taxonomy assumption) and 5 real surviving mutations. Claude fixed all of them with regression tests and re-mutated the fixes (5/5 killed).

---

## 1:40 — Ship

```
skip S6, do README and ship
```
README written from real output, `docs/DISCUSSION_NOTES.md` filled, fresh-clone test, secret scan, tag `v1.0-submission` created locally. **Push is gated on my approval** (nothing is pushed without it).

---

## After the box — extra human time

```
Though you're past 90 agent minutes, we still have 50 more human minutes if you want to fix/improve/build things that matter. Also make sure to update docs/PROMPTS.md to match the sequence of steps we actually took and the timeframes we used.
```
Claude rewrote this file and, with the extra time, built S6 (A-001 stub suggester with guardrails, opt-in via `--suggest` so the reviewed golden file stays unchanged). See `docs/AI_USAGE.md` and `docs/DECISIONS.md` for what was added and verified.

---

## Recovery prompts (kept from the kit; not needed so far)

- Going off-plan: `Stop. Revert uncommitted changes with git restore. Re-read CLAUDE.md §1 and the current slice in SPEC.md, then redo only <X> touching only <files>.`
- A test was weakened: `You changed an assertion in <test>. That is not allowed (CLAUDE.md §1.4). Restore the original assertion and fix the implementation instead.`
- Too much code: `This is more code than the slice needs. Show me the smallest change that meets the acceptance criteria.`
- Unsure about AI output: `Explain this function line by line and give me two inputs where it would give a wrong answer.`
