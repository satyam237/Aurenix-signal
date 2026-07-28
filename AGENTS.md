# AureniX Signal — Agent Guide

Guidance for AI coding agents and humans working in this repo.

**Read first:** [`PLAN.md`](PLAN.md) (progress) → [`STATUS.md`](STATUS.md) (snapshot) → this file (conventions) → [`README.md`](README.md) (setup).

## What this project is

GEO (AI Discovery Optimization) for **The Nautikal**: automate “what do ChatGPT/Gemini say?”, score answers into a **GEO Score**, later recommend content fixes.

**Current stage:** Phases **0–2 done and on org `main` (PR #2)**. Do not start Phase 4. Prefer **Phase 3** (prompt table + response viewer) unless asked otherwise.

## How it works (data flow)

1. Prompts from `data/prompts/` (+ optional brand system prompt from truth registry)
2. `prompt_runner` adapters call OpenAI / Gemini → rows in `raw_runs` / `run_batches`
3. `response_judge` scorers write `scores` (inclusion, rank, accuracy, citation, sentiment, geo_score)
4. `dashboard/health_app.py` shows batch health + GEO rollups (Inclusion %, Avg Rank, Avg Accuracy, Avg GEO; SoV by category)
5. Phase 3 will add prompt table + response viewer (prompt text + AI answer + scores together)

## Repository layout

```
backend/
  agents/prompt_runner/     Phase 1 — adapters + pipeline
  agents/response_judge/    Phase 2 — inclusion, rank, accuracy, citation, sentiment, composite
  scheduler/                cron_runner.py (--force for local)
  shared/                   config, supabase, brand_context, pricing, concurrency
dashboard/health_app.py     Streamlit ops + GEO panel
data/brands|prompts|baseline/
supabase/migrations/        001 schema, 002 score cols, 003 PDF score cols
scripts/                    run_daily_local, backfill, calibrate, seed, apply_schema, …
tests/                      mocked pytest (41)
deploy/                     optional GCP (not required for local prod path)
docs/                       roadmap PDF
```

## Commands

```bash
pip install -e ".[dev]"          # or: pip install -r requirements.txt && pip install -e ".[dev]"
python -m pytest tests/ -q
python scripts/check_ready.py
./scripts/run_daily_local.sh
python scripts/backfill_scores.py --supabase --skip-llm --rescore
python scripts/calibrate_scores.py --limit 25
streamlit run dashboard/health_app.py
```

## Non-negotiables

1. Imports use `backend.` namespace only.
2. Brand facts only from `data/brands/nautikal_truth_registry.json` (via `brand_context.py`).
3. Tests mock all network — never hit live OpenAI/Gemini/Supabase in pytest.
4. Live API calls cost money — use `--limit` / `--skip-llm` while developing.
5. Never commit `.env`, `data/runs/`, `data/scores/`, `__pycache__`.
6. Keep model names in `backend/shared/config.py` synced with `pricing.py`.
7. GEO weights live in `response_judge/weights.py` (PDF: 0.25/0.25/0.20/0.15/0.15).

## Environment

`.env`: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (+ optional `SUPABASE_DB_PASSWORD`).

## Git

- Remotes: `org` = The-Aurenix/aurenix-signal · `origin` = satyam237/Aurenix-signal  
- Branch: `restructure/signal-mvp` → merge target `main`  
- Run tests before commit. Update `PLAN.md` / `STATUS.md` at session end.

## Session end checklist

Update `PLAN.md` §2–4 and refresh `STATUS.md` if stage or open items changed.
