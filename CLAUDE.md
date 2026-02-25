# Claude Code Instructions for ThirdLayer-Prototype

## Goal
Implement a runnable repo that matches the architecture and constraints in this repository.

## Non-negotiables
- Keep module boundaries: predictor suggests; planner selects; validator filters; executor acts; metrics measures.
- Do NOT add new dependencies unless absolutely necessary.
- Use stdlib `sqlite3` (no ORM).
- Use async Playwright API.
- Keep schema in `src/db/schema.sql` consistent.

## Output expectations (if generating code)
- Fill in TODOs and implement functions.
- Ensure `python demo/run_demo.py` runs end-to-end.
- Ensure `uvicorn src.main:app --reload` starts and `/metrics` works.

## Acceptance checks
- `pytest -q` passes.
- Recording mode inserts actions into SQLite.
- Autopilot mode executes actions only above confidence threshold and passes validator.
- `/transitions/top?k=10` returns a JSON list.
- `/metrics` returns required metrics keys.

## Avoid
- monolithic scripts
- hardcoding selectors beyond demo workflow
- skipping error handling/timeouts