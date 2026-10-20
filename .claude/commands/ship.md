---
description: Final submission checklist — fresh-clone test, README, tag, push
---
Run the submission checklist in CLAUDE.md §10:

1. `make check` and `make demo` — paste test summary and demo output into README.
2. Fresh-clone test: clone the repo into a scratch folder, run `make setup && make demo`, confirm it works offline from a clean checkout.
3. Secret scan: `git grep -nIi -e "sk-ant" -e "api_key=" -e "password="` — must find nothing real.
4. README final pass against the brief's 'Deliverables' list: implementation, how to run/test, sample input/output, tests run, assumptions & trade-offs, AI usage, what works / incomplete / risks / next.
5. Commit `docs: final submission`, tag `v1.0-submission`.
6. Ask me before running `git push origin main --tags`. $ARGUMENTS
