# CLAUDE.md — AureniX Signal

Project guidance for AI coding agents lives in **`AGENTS.md`** (layout, commands, conventions, environment, git workflow). Read it first and follow it.

Quick orientation:

- **What this is:** GEO (AI Discovery Optimization) platform measuring brand visibility in AI engine responses. Case-study brand: The Nautikal.
- **Work plan & progress log:** `PLAN.md` — read it at session start, update it at session end (phase checkboxes, work log, decisions).
- **Status snapshot:** `STATUS.md` — Phases 0–1 done, Phase 2 (Response Judge + GEO Score) is next.
- **Setup for humans:** `README.md`.

Non-negotiables:

1. Run `python3 -m pytest tests/ -q` before committing — all tests must pass.
2. Imports use the `backend.` namespace; the repo follows the org `aurenix-signal` skeleton layout.
3. Never commit secrets (`.env`), run artifacts (`data/runs/`), or `__pycache__`.
4. Live API calls cost money — use `scripts/bulk_prompt_test.py --limit 3` for smoke tests; tests must mock all network calls.
5. Brand facts come only from `data/brands/nautikal_truth_registry.json`.
