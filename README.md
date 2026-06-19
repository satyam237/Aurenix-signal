# AureniX Signal

AI Discovery Optimization (GEO) platform that measures how brands appear in AI engine responses and recommends content fixes to improve recommendation rates.

**Case study brand:** [The Nautikal](https://thenautikal.com) — cruise travel accessories and curated essentials kits.

**Hypothesis (v1.0 MVP):** targeted content changes increase a brand's AI recommendation rate, measured by a composite **GEO Score**.

## Architecture

```
agents/prompt_runner/   → Phase 1: automated prompt execution
shared/                 → config, Supabase client, models, pricing
scheduler/              → Cron entry point
dashboard/              → Streamlit health dashboard (Phase 1)
data/                   → prompts, truth registry, baseline CSV
supabase/migrations/    → database schema
scripts/                → seed, API smoke tests, baseline helpers
```

| Layer | v1.0 Choice |
|-------|-------------|
| Backend | Python monorepo |
| Database | Supabase (`prompts`, `raw_runs`, `run_batches`, `brand_config`, `scores`) |
| AI engines | OpenAI (`gpt-4o-mini`) + Gemini (`gemini-2.0-flash`) |
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

Full roadmap: [`data/pdf/AureniX_Signal_Roadmap_Updated.pdf`](data/pdf/AureniX_Signal_Roadmap_Updated.pdf)

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
# Fill in OPENAI_API_KEY, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
```

### 3. Apply Supabase schema

Create a Supabase project, then run the migration in [`supabase/migrations/001_initial_schema.sql`](supabase/migrations/001_initial_schema.sql) via the Supabase SQL editor or CLI:

```bash
supabase db push   # if using Supabase CLI linked to project
```

Seed prompts and brand config:

```bash
python scripts/seed_supabase.py
```

### 4. Verify API keys

```bash
python scripts/test_api_keys.py
```

## Running Phase 1

### Manual pipeline run

```bash
python -m agents.prompt_runner.pipeline
```

### Cron scheduler (daily 6 AM UTC)

```bash
python -m scheduler.cron_runner
```

Local crontab example:

```
0 6 * * * cd /path/to/GEO-Ranker-Signal-15June && .venv/bin/python -m scheduler.cron_runner
```

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
GEO-Ranker-Signal-15June/
├── agents/prompt_runner/
│   ├── pipeline.py
│   └── adapters/
├── shared/
├── scheduler/
├── dashboard/
├── data/
├── supabase/migrations/
└── scripts/
```
