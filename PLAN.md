# PLAN.md — AureniX Signal Work Plan & Progress Log

> **This is the living source of truth for project progress.** Every developer and AI agent session should read this file first to resume with context, and **update it before ending a session** (tick checkboxes, append to the work log, record decisions/modifications).
>
> Companion docs: `STATUS.md` (current snapshot), `AGENTS.md` / `CLAUDE.md` (agent conventions), `README.md` (human setup).

---

## 1. Project overview

**Goal:** GEO (AI Discovery Optimization) platform that measures how brands appear in AI engine responses and recommends content fixes to improve recommendation rates.

- **Case-study brand:** The Nautikal (cruise travel accessories, thenautikal.com)
- **Hypothesis (v1.0):** targeted content changes increase a brand's AI recommendation rate, measured by a composite **GEO Score**
- **Stack:** Python 3.11+ monorepo · Supabase · OpenAI (`gpt-5-mini`) + Gemini · Streamlit · Cron
- **Repos:** `org` = The-Aurenix/aurenix-signal (canonical) · `origin` = satyam237/Aurenix-signal (fork)
- **Active branch:** `restructure/signal-mvp` → merge target: org `main` (**pending review**)
- **Full roadmap:** `docs/AureniX_Signal_Roadmap_Updated.pdf`

## 2. Phase plan & progress

### Phase 0 — Baseline & scaffold ✅ COMPLETE
- [x] Monorepo scaffold (`backend/`, `dashboard/`, `data/`, `scripts/`, `supabase/`, `tests/`)
- [x] Truth Registry — `data/brands/nautikal_truth_registry.json`
- [x] Prompt library — `data/prompts/nautikal_prompts.json` (25 prompts, brand-steered) + `nautikal_prompts_neutral.json` (neutral baseline set)
- [x] Supabase schema — `supabase/migrations/001_initial_schema.sql` (`prompts`, `raw_runs`, `run_batches`, `brand_config`, `scores`)
- [x] Baseline template + CSV — `data/baseline/week0_baseline.csv`, `scripts/generate_baseline_template.py`
- [ ] Week-0 manual baseline recorded on ChatGPT/Gemini UIs (data-entry task, not code)

### Phase 1 — Prompt Runner ✅ COMPLETE (code); production cron pending
- [x] Engine adapters (OpenAI + Gemini) with retry via tenacity — `backend/agents/prompt_runner/adapters/`
- [x] Pipeline: prompts → engines → Supabase `raw_runs` — `backend/agents/prompt_runner/pipeline.py`
- [x] Cron entry point (daily 6 AM UTC) — `backend/scheduler/cron_runner.py`
- [x] Health dashboard — `dashboard/health_app.py` (Streamlit)
- [x] Seed + readiness scripts — `scripts/seed_supabase.py`, `check_ready.py`, `test_api_keys.py`
- [x] Verification script — `scripts/verify_phase1.py`
- [x] Schema apply tooling — `scripts/apply_schema.py`, `scripts/setup_supabase.sh`
- [x] GCP deploy assets — `Dockerfile`, `deploy/gcp_deploy.sh`, `deploy/README.md`
- [x] **Schema applied on live Supabase project** (`wjfxtmjjwezsamgiktzf`)
- [ ] **GCP cron deployed** ← `gcloud auth login` + `./deploy/gcp_deploy.sh all`
- [ ] **Exit criteria confirmed in production:** 50+ runs/day, >95% success rate, results queryable in `raw_runs`

### Phase 1.5 — Concurrency & brand grounding (added scope) ✅ COMPLETE
- [x] Concurrent multi-engine runner with rate limiting — `backend/shared/concurrent_runner.py`, `rate_limiter.py`
- [x] Checkpointing (partial saves every 5 completions) + cost tracking — `backend/shared/pricing.py`
- [x] Task filtering/skipping in runner
- [x] Brand-grounding system-prompt generator from truth registry — `backend/shared/brand_context.py`
- [x] System prompt threaded through adapters → runner → pipeline → bulk script
- [x] Bulk test tooling (Supabase-free) — `scripts/bulk_prompt_test.py` (`--limit`, `--concurrency`, `--sequential`, `--no-brand-context`)
- [x] Test suite: 23 tests, all mocked, all passing

### Phase 2 — Response Judge + GEO Score 🚧 IN PROGRESS
- [x] Define GEO Score components (brand mention, recommendation position, sentiment, factual accuracy vs. truth registry)
- [x] Response Judge agent — classify/score each `raw_runs` row — `backend/agents/response_judge/`
- [x] Persist scores to Supabase `scores` table (migration `002_scores_columns.sql` applied)
- [x] Scoring backfill over existing run data in `data/runs/` — `scripts/backfill_scores.py --local`
- [x] Tests for judge + scoring — `tests/test_response_judge.py` (32 total suite)
- [x] Supabase backfill of unscored `raw_runs` (heuristic) — 8/8 scored, avg GEO ~0.76

### Phase 3 — GEO Dashboard MVP ⏳ NOT STARTED
- [ ] Score trends over time per engine/prompt category
- [ ] Brand-grounded vs. neutral comparison view

### Phase 4 — GEO Recommender + before/after loop ⏳ NOT STARTED
- [ ] Content-fix recommendations from low-scoring responses
- [ ] Before/after measurement loop to validate the v1.0 hypothesis

## 3. Work log (append new entries at top)

### 2026-07-28 — Productionize Phase 1 + start Phase 2
- Committed/pushed Jul 13 docs, Supabase tooling, and GCP deploy assets to `org` + `origin` on `restructure/signal-mvp`.
- Supabase project `wjfxtmjjwezsamgiktzf` resumed; verified 001 tables + seed (25 prompts). Pipeline smoke: 4/4 success (~$0.008).
- Built Response Judge (`backend/agents/response_judge/`), migration `002_scores_columns.sql`, `scripts/backfill_scores.py`; local heuristic backfill scored 50 bulk rows. Suite now 32 tests.
- **Blocked on:** paste/run migration 002 in SQL editor (no `SUPABASE_DB_PASSWORD`; `db.*.supabase.co` DNS not resolving yet). GCP: gcloud installed, auth/deploy pending.

### 2026-07-13 (evening) — Supabase setup tooling + GCP cron deploy assets
- Added `scripts/apply_schema.py` (SQL editor instructions, optional `--apply` via `SUPABASE_DB_PASSWORD`), `scripts/setup_supabase.sh` (schema check → seed → pipeline smoke).
- Added `Dockerfile`, `.dockerignore`, `deploy/gcp_deploy.sh`, `deploy/README.md` for Cloud Run Jobs + Cloud Scheduler (free-tier path; Vertex AI not needed — uses OpenAI/Gemini APIs directly).
- Verified API keys + Supabase URL in `.env`; confirmed schema **not yet applied** on project `wjfxtmjjwezsamgiktzf` (tables missing). Seed blocked until SQL editor step.
- GCP deploy script validated; `gcloud` not installed locally — deploy pending.

### 2026-07-13 (PM) — Repo restructure + org integration
- Restructured flat layout → org `aurenix-signal` skeleton (`backend.` namespace); updated all imports, string module refs, test mocks, `pyproject.toml` packaging, docs/help text. Verified with ruff + full test suite.
- Removed `.gitkeep` placeholders; pushed `restructure/signal-mvp` to `org` and `origin`; PR toward org `main` opened (org OAuth restrictions blocked `gh`-based PR creation initially).
- Added `STATUS.md`, `AGENTS.md`, `CLAUDE.md`, `PLAN.md`; linked from `README.md`.

### 2026-07-13 (AM) — Brand grounding + concurrency
- Built brand-grounding system-prompt generator from the Nautikal truth registry; strengthened brand-steered prompt library (neutral set preserved separately for baselines).
- Implemented concurrent task runner (rate limiting, checkpointing, cost tracking, task filtering); threaded system-prompt support through adapters, pipelines, and bulk script.
- Fixed `before_task` callback propagation in the sequential execution path.
- Ran bulk tests (`data/runs/bulk_test_20260713_*.json`); added test coverage for runner, bulk script, brand grounding.

### Earlier — Phase 0–1 foundation
- Initial scaffold, Supabase schema, prompt library, adapters, pipeline, cron runner, health dashboard, seed/readiness scripts.
- Model update: `gpt-5-mini` / `gemini-2.5-flash` + bulk test tooling (PR #1 on fork).

## 4. Decisions & modifications log

| Date | Decision / change | Rationale |
|------|-------------------|-----------|
| 2026-07-28 | GEO Score weights: mention 0.30 / position 0.25 / sentiment 0.20 / accuracy 0.25 | Emphasize visibility (mention+position) while retaining quality signals |
| 2026-07-28 | Judge: deterministic alias match + LLM soft scores (gpt-5-mini) | Cheap/testable mention detection; LLM for sentiment/factual accuracy vs registry |
| 2026-07-13 | GCP cron via Cloud Run Jobs + Cloud Scheduler (not Vertex AI) | Free-tier infra; LLM calls stay on OpenAI/Gemini API keys |
| 2026-07-13 | Schema apply via SQL editor or `apply_schema.py --apply` | User's Supabase project not linkable via CLI (different account) |
| 2026-07-13 | Repo restructured to org skeleton; imports under `backend.` namespace | Match org `aurenix-signal` layout for merge into org repo |
| 2026-07-13 | Bulk runs default to **brand-grounded** mode; `--no-brand-context` flag for neutral | Grounding forces verified Nautikal facts; neutral mode kept as measurement baseline |
| 2026-07-13 | Brand-steered prompts split from neutral set (two JSON files) | Keep baseline comparable across runs |
| Earlier | Models set to `gpt-5-mini` + Gemini flash tier | Cost control for daily runs |
| Earlier | Sequential worker + cron over task queues | v1.0 simplicity; concurrency added later in-process |

## 5. Dependencies

Runtime (`pyproject.toml`): `openai>=1.40`, `google-genai>=1.0`, `supabase>=2.7`, `pydantic>=2.8`, `pydantic-settings>=2.4`, `python-dotenv>=1.0`, `tenacity>=8.5`, `streamlit>=1.38`. Dev: `pytest>=8.3`, `ruff>=0.6` (line length 100, py311).

External services: Supabase project (schema in `supabase/migrations/`), OpenAI API, Gemini API. Secrets in `.env` (see `README.md`); validate with `scripts/check_ready.py`.

Internal coupling to know about:
- Model names in `backend/shared/config.py` must stay in sync with prices in `backend/shared/pricing.py`.
- `backend/shared/brand_context.py` is the **only** consumer of the truth registry — don't hardcode brand facts elsewhere.
- `scripts/bulk_prompt_test.py` bypasses Supabase entirely; the pipeline requires it.

## 6. Known issues / open items

- [x] Apply Supabase schema 001 on `wjfxtmjjwezsamgiktzf`
- [x] Seed + pipeline smoke (`verify_phase1` OK; smoke batch success=4)
- [ ] Apply migration `002_scores_columns.sql` (GEO Score columns) — paste in SQL editor or set `SUPABASE_DB_PASSWORD`
- [ ] Install gcloud + deploy cron — gcloud installed; need `gcloud auth login` + `./deploy/gcp_deploy.sh all`
- [ ] `restructure/signal-mvp` → org `main` merge pending review.
- [ ] Phase 1 exit criteria not yet proven in production (daily cron).
- [ ] Week-0 manual baseline CSV not filled in.
- [ ] Neutral vs. brand-grounded comparison run not yet executed/analyzed.
- Note: brand-grounded API runs are a **measurement instrument** — they do not influence public model behavior.

## 7. Session resume checklist (for every new dev/agent session)

1. Read this file, then `AGENTS.md` for conventions.
2. `git fetch --all` and check you're on the right branch (`git status`).
3. `python3 -m pytest tests/ -q` — 32 tests should pass before you start.
4. Pick up from §6 open items or the current phase in §2.
5. **Before ending:** update §2 checkboxes, prepend a §3 work-log entry, record any §4 decisions, and refresh `STATUS.md` if the snapshot changed.
