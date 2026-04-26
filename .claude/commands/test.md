---
description: Run all backend checks (tests, lint, type check)
---

Run the full backend quality gate from `server/`:

1. `pytest` — unit tests must all pass
2. `ruff check src tests` — linter
3. `mypy src` — strict type checking

Report any failures with file:line references. If everything passes, summarize: number of tests, lint clean, types clean.
