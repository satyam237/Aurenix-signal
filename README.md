# AureniX Signal

AI Discovery Optimization (GEO) platform that measures how brands appear in AI engine responses and recommends content fixes to improve recommendation rates.

**Case study brand:** [The Nautikal](https://thenautikal.com) — cruise travel accessories and curated essentials kits.

**Hypothesis (v1.0 MVP):** targeted content changes increase a brand's AI recommendation rate, measured by a composite **GEO Score**.

**Project status:** Phases 0–1 complete — snapshot in [`STATUS.md`](STATUS.md), living work plan & progress log in [`PLAN.md`](PLAN.md). AI agent guidance: [`AGENTS.md`](AGENTS.md) / [`CLAUDE.md`](CLAUDE.md).

## Architecture

```
backend/agents/prompt_runner/  → Phase 1: automated prompt execution
backend/shared/                → config, Supabase client, models, pricing
backend/scheduler/             → Cron entry point
dashboard/                     → Streamlit health dashboard (Phase 1)
data/                          → prompts, truth registry, baseline CSV
docs/                          → roadmap and reference documents
experiments/                   → ad-hoc experiments and analysis
supabase/migrations/           → database schema
scripts/                       → seed, API smoke tests, baseline helpers
tests/                         → pytest suite
```

| Layer | v1.0 Choice |
|-------|-------------|
| Backend | Python monorepo |
| Database | Supabase (`prompts`, `raw_runs`, `run_batches`, `brand_config`, `scores`) |
| AI engines | OpenAI (`gpt-5-mini`) + Gemini (`gemini-3-flash-preview`) |
| Orchestration | Sequential Python worker + Cron |
| Ops UI | Streamlit health dashboard |

## Roadmap phases

| Phase | Focus |
|-------|-------|
| 0 | Baseline, Truth Registry, Supabase, monorepo scaffold |
| 1 | Prompt Runner — automated daily runs → Supabase |
| 2 | Response Judge + GEO Score |
| 3 | GEO Dashboard MVP |
| 4 | GEO Recommender + before/after loop |

Full roadmap: [`docs/AureniX_Signal_Roadmap_Updated.pdf`](docs/AureniX_Signal_Roadmap_Updated.pdf)

## Setup

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your keys (required before any live runs):

| Variable | Required for | Where to get it |
|----------|--------------|-----------------|
| `OPENAI_API_KEY` | OpenAI prompt runs | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `GEMINI_API_KEY` | Gemini prompt runs | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `SUPABASE_URL` | Pipeline + dashboard | Supabase project → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Pipeline + dashboard | Same page (service role, server-side only) |

Check readiness:

```bash
python scripts/check_ready.py
```

### 3. Apply Supabase schema

See [`supabase/README.md`](supabase/README.md) for full details.

```bash
python scripts/apply_schema.py --print-sql   # opens SQL editor instructions
python scripts/apply_schema.py --check-only  # verify all 5 tables exist
python scripts/setup_supabase.sh             # seed + smoke pipeline (after schema)
```

Paste [`supabase/migrations/001_initial_schema.sql`](supabase/migrations/001_initial_schema.sql) into the Supabase SQL editor, or set `SUPABASE_DB_PASSWORD` in `.env` and run `python scripts/apply_schema.py --apply`.

Seed prompts and brand config:

```bash
python scripts/seed_supabase.py
```

### 4. Verify API keys

```bash
python scripts/test_api_keys.py
```

## Bulk testing prompts (no Supabase required)

Smoke-test API keys, then run prompts from the local JSON library and save results to disk:

```bash
python scripts/check_ready.py          # confirms keys are set
python scripts/test_api_keys.py        # one prompt per engine
python scripts/bulk_prompt_test.py --limit 3              # quick test (3 prompts × engines)
python scripts/bulk_prompt_test.py --concurrency 6        # full run, parallel (~4-5 min)
python scripts/bulk_prompt_test.py --concurrency 2        # conservative parallelism
python scripts/bulk_prompt_test.py --sequential           # one call at a time (debug)
python scripts/bulk_prompt_test.py --no-brand-context     # neutral mode (no brand grounding)
```

By default, runs inject a brand-grounding system prompt built from
`data/brands/nautikal_truth_registry.json` so engines answer with verified
Nautikal facts. Prompts in `data/prompts/nautikal_prompts.json` are brand-steered;
the original neutral prompt set is preserved in
`data/prompts/nautikal_prompts_neutral.json` for baseline measurement.

Results are written to `data/runs/bulk_test_<timestamp>.json`. Partial progress is checkpointed every 5 completions to `*.partial.json`.

## Running Phase 1 (with Supabase)

### Manual pipeline run

```bash
python -m backend.agents.prompt_runner.pipeline
python -m backend.agents.prompt_runner.pipeline --limit 3   # first 3 prompts only (testing)
```

### Cron scheduler (daily 6 AM UTC)

```bash
python -m backend.scheduler.cron_runner
```

Local crontab example:

```
0 6 * * * cd /path/to/aurenix-signal && .venv/bin/python -m backend.scheduler.cron_runner
```

### GCP Cloud Run Jobs (recommended for production cron)

Free-tier friendly: Cloud Scheduler (3 free jobs) + Cloud Run Jobs. See [`deploy/README.md`](deploy/README.md).

```bash
export GCP_PROJECT_ID=your-gcp-project-id
./deploy/gcp_deploy.sh all    # secrets + deploy + daily 6 AM UTC schedule
./deploy/gcp_deploy.sh run    # manual test execution
```

Requires [gcloud CLI](https://cloud.google.com/sdk/docs/install). Uses `Dockerfile` at repo root; secrets from `.env` via Secret Manager.

### Health dashboard

```bash
streamlit run dashboard/health_app.py
```

## Phase 0 baseline (manual)

1. Prompts live in [`data/prompts/nautikal_prompts.json`](data/prompts/nautikal_prompts.json)
2. Run each prompt manually on ChatGPT and Gemini
3. Record results in [`data/baseline/week0_baseline.csv`](data/baseline/week0_baseline.csv)
4. Generate empty template: `python scripts/generate_baseline_template.py`

## Phase 1 exit criteria

- 50+ prompt runs/day (25 prompts × 2 engines)
- >95% success rate
- Results queryable in Supabase `raw_runs`
- Health dashboard shows batch metrics

## Project structure

```
aurenix-signal/
├── backend/
│   ├── agents/prompt_runner/
│   │   ├── pipeline.py
│   │   └── adapters/
│   ├── shared/
│   └── scheduler/
├── dashboard/
├── data/
├── docs/
├── experiments/
├── supabase/migrations/
├── scripts/
└── tests/
```
