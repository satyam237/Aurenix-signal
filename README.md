# AureniX Signal

**AI Discovery Optimization (GEO)** platform: measure how a brand appears in AI engine answers, score that visibility, and (later) recommend content fixes.

| | |
|--|--|
| **Stage** | **Phases 0–2 complete locally.** Phase 3 (GEO Dashboard MVP) is next. |
| **Case study** | [The Nautikal](https://www.thenautikal.com) — cruise travel accessories |
| **Hypothesis** | Targeted content changes raise AI recommendation rate, measured by a composite **GEO Score** |
| **Branch** | `restructure/signal-mvp` → org `main` |
| **Roadmap** | [`docs/AureniX_Signal_Roadmap_Updated.pdf`](docs/AureniX_Signal_Roadmap_Updated.pdf) |
| **Status snapshot** | [`STATUS.md`](STATUS.md) · living plan [`PLAN.md`](PLAN.md) · agents [`AGENTS.md`](AGENTS.md) |

## What it does

1. **Prompt Runner (Phase 1)** — runs 25 brand prompts against OpenAI + Gemini, stores raw answers in Supabase (`raw_runs` / `run_batches`).
2. **Response Judge (Phase 2)** — scores each answer: Inclusion, Rank, Accuracy, Citation, Sentiment → composite GEO Score + Share-of-Voice.
3. **Ops UI** — Streamlit health dashboard with batch health **and** GEO score metrics (not the full Phase 3 product dashboard yet).

## Architecture

```
                    ┌─────────────────────┐
   prompts JSON ───▶│  prompt_runner      │──▶ OpenAI / Gemini
   truth registry ─▶│  (adapters+pipeline)│
                    └─────────┬───────────┘
                              │ raw_runs
                              ▼
                    ┌─────────────────────┐
                    │  response_judge     │──▶ scores (GEO + SoV)
                    │  inclusion/rank/…   │
                    └─────────┬───────────┘
                              ▼
              Supabase ◀── Streamlit health_app (ops + GEO panel)
                              ▲
              cron_runner / run_daily_local.sh
```

| Path | Role |
|------|------|
| `backend/agents/prompt_runner/` | Engine adapters + pipeline → Supabase |
| `backend/agents/response_judge/` | PDF scorers (T-10–T-14) + composite GEO/SoV |
| `backend/scheduler/` | Cron entry (`--force` for local anytime) |
| `backend/shared/` | Config, Supabase client, brand context, pricing, concurrency |
| `dashboard/health_app.py` | Streamlit: run health + GEO metrics |
| `data/brands/` | Truth registry (only source of brand facts) |
| `data/prompts/` | Brand-steered + neutral prompt libraries |
| `supabase/migrations/` | `001` schema · `002` score stub cols · `003` PDF score cols |
| `scripts/` | Seed, daily local run, backfill, calibrate, schema helpers |
| `tests/` | Mocked pytest suite (no live network) |
| `deploy/` | Optional GCP Cloud Run + Scheduler (deferred) |

**Stack:** Python 3.11+ · Supabase · OpenAI (`gpt-5-mini`) · Gemini · Streamlit · tenacity retries

**GEO formula (roadmap):**  
`(0.25×Inclusion) + (0.25×Rank) + (0.20×Accuracy) + (0.15×Citation) + (0.15×Sentiment)`  
SoV = included prompts / scored prompts × 100 (by category).

## Roadmap phases

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Baseline, Truth Registry, schema, scaffold | Done |
| 1 | Prompt Runner → Supabase (+ local cron) | Done locally; GCP optional |
| 2 | Response Judge + GEO Score | Done locally |
| 3 | GEO Dashboard MVP (T-16–T-19) | **Next** |
| 4 | Recommender + before/after loop | Not started |

## Setup

### 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# or: pip install -r requirements.txt && pip install -e ".[dev]"
```

### 2. Environment

```bash
cp .env.example .env
```

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI runs + sentiment judge |
| `GEMINI_API_KEY` | Gemini runs + accuracy judge |
| `SUPABASE_URL` | Persistence + dashboard |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side Supabase (never expose to browsers) |
| `SUPABASE_DB_PASSWORD` | Optional — apply migrations via `--apply` |

```bash
python scripts/check_ready.py
```

### 3. Schema

Apply migrations `001` → `003` (SQL editor or `python scripts/apply_schema.py --print-sql`).  
Then: `python scripts/seed_supabase.py` (or `./scripts/setup_supabase.sh`).

## Daily local operations (no GCP)

```bash
./scripts/run_daily_local.sh                 # pipeline --force + heuristic score backfill
./scripts/run_daily_local.sh --llm           # LLM accuracy/sentiment (costs API)
python scripts/backfill_scores.py --supabase --skip-llm --rescore
python scripts/calibrate_scores.py --limit 25
streamlit run dashboard/health_app.py
```

Cheap smoke (no Supabase): `python scripts/bulk_prompt_test.py --limit 3`

## Tests

```bash
python -m pytest tests/ -q   # must pass before commit; all network mocked
```

## Optional GCP cron

See [`deploy/README.md`](deploy/README.md). Local path above is the supported default until Cloud Run is redeployed.

## License / remotes

- Canonical: `The-Aurenix/aurenix-signal` (`org`)
- Fork: `satyam237/Aurenix-signal` (`origin`)
