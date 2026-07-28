# AureniX Signal — Agent Guide

AI Discovery Optimization (GEO) platform: measures how brands appear in AI engine responses and recommends content fixes. Case-study brand: The Nautikal (cruise travel accessories). Python monorepo, Supabase persistence, OpenAI + Gemini engines.

**Start every session by reading [`PLAN.md`](PLAN.md)** — it holds the phase progress, work log, decisions, and open items, and must be updated before you end a session (see its §7 checklist). `STATUS.md` is the current snapshot; `README.md` covers human setup.

Supabase setup: `python scripts/apply_schema.py --print-sql` then `scripts/setup_supabase.sh`. GCP cron: `deploy/gcp_deploy.sh`.

## Layout

```
backend/agents/prompt_runner/   Phase 1 pipeline (pipeline.py + adapters/)
backend/shared/                 config, models, supabase_client, brand_context,
                                concurrent_runner, rate_limiter, pricing
backend/scheduler/              cron_runner.py (daily 6 AM UTC entry point)
dashboard/                      Streamlit health dashboard (health_app.py)
data/prompts/                   nautikal_prompts.json (brand-steered),
                                nautikal_prompts_neutral.json (baseline)
data/brands/                    nautikal_truth_registry.json (source of brand facts)
data/runs/                      bulk test outputs (gitignored artifacts)
supabase/migrations/            schema: prompts, raw_runs, run_batches, brand_config, scores
scripts/                        bulk_prompt_test.py, seed_supabase.py, check_ready.py,
                                test_api_keys.py, verify_phase1.py
tests/                          pytest suite
```

## Commands

```bash
pip install -e ".[dev]"                          # install (from repo root)
python3 -m pytest tests/ -q                      # run tests (must pass before commit)
python scripts/check_ready.py                    # verify .env keys are set
python scripts/bulk_prompt_test.py --limit 3     # cheap smoke run (no Supabase)
python -m backend.agents.prompt_runner.pipeline  # full Phase 1 pipeline (needs Supabase)
streamlit run dashboard/health_app.py            # health dashboard
```

## Conventions

- Imports use the `backend.` namespace (e.g. `from backend.shared.config import ...`). Never reintroduce top-level `shared`/`agents` imports — the repo was restructured to the org skeleton on 2026-07-13.
- Engine/model names live in `backend/shared/config.py`; pricing in `backend/shared/pricing.py`. Update both when changing models.
- Brand facts come only from `data/brands/nautikal_truth_registry.json`. Do not hardcode Nautikal product claims elsewhere; `backend/shared/brand_context.py` builds the grounding system prompt from the registry.
- Bulk runs default to brand-grounded mode; pass `--no-brand-context` for neutral baseline measurement. Keep the neutral prompt set (`nautikal_prompts_neutral.json`) unchanged so baselines stay comparable.
- Live API calls cost money. Use `--limit 3` / `--sequential` while developing; the concurrent runner checkpoints partial progress to `data/runs/*.partial.json`.
- Tests mock all network calls — never add tests that hit live OpenAI/Gemini/Supabase.

## Environment

Secrets in `.env` (never commit): `OPENAI_API_KEY`, `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`. `scripts/check_ready.py` validates them.

## Git

- Remotes: `org` = The-Aurenix/aurenix-signal (canonical), `origin` = satyam237/Aurenix-signal (fork).
- Active branch: `restructure/signal-mvp`; merge target is org `main`.
- Run the test suite before committing. Don't commit `data/runs/` artifacts, `.env`, or `__pycache__`.
