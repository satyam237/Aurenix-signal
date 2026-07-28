# Project Status — AureniX Signal

_Last updated: 2026-07-28_

> Snapshot only. The living work plan, progress checkboxes, work log, and decisions are in [`PLAN.md`](PLAN.md) — update that file as work progresses.

## Summary

Phases 0–1 are **live on Supabase** (seeded + pipeline smoke succeeding). Phase 2 Response Judge + GEO Score **code is in** (migration 002 pending apply). GCP cron needs `gcloud auth login` + project id.

## Current state

| Item | Status |
|------|--------|
| Active branch | `restructure/signal-mvp` |
| Test suite | 32/32 passing |
| API keys in `.env` | OpenAI + Gemini + Supabase service role configured |
| Supabase project `wjfxtmjjwezsamgiktzf` | **Resumed / live** |
| Supabase schema (001) | Applied — 5 tables present, prompts seeded (25) |
| Migration 002 (scores GEO columns) | **Pending** — paste `supabase/migrations/002_scores_columns.sql` in SQL editor |
| Pipeline smoke | OK — batch success=4 failure=0 (~$0.008) |
| GCP cron deploy | gcloud installed; **auth + deploy pending** |

## Immediate manual steps

1. **Apply migration 002** — open [SQL editor](https://supabase.com/dashboard/project/wjfxtmjjwezsamgiktzf/sql/new), paste `supabase/migrations/002_scores_columns.sql`, Run.
2. **GCP auth** — `gcloud auth login` then `export GCP_PROJECT_ID=...` and `./deploy/gcp_deploy.sh all`

## Phase progress

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Baseline, Truth Registry, Supabase schema, monorepo scaffold | ✅ Done |
| 1 | Prompt Runner — automated daily runs → Supabase | ✅ Live (cron deploy pending) |
| 2 | Response Judge + GEO Score | 🚧 Code done; migration 002 apply pending |
| 3 | GEO Dashboard MVP | ⏳ Not started |
| 4 | GEO Recommender + before/after loop | ⏳ Not started |

## What's new (Jul 28)

- Response Judge agent (`backend/agents/response_judge/`) with brand-mention heuristics + LLM soft scores + composite GEO Score
- Migration `002_scores_columns.sql` + `scripts/backfill_scores.py`
- Local heuristic backfill over `data/runs` artifacts
- `scripts/apply_schema.py` applies all migrations in order; `verify_phase1` fixed for `brand_config.brand_id`

## Next steps

- [ ] Paste/run migration 002 on live Supabase
- [ ] `python scripts/backfill_scores.py --supabase --skip-llm` (then LLM judge with care)
- [ ] Deploy GCP cron via `./deploy/gcp_deploy.sh all`
- [ ] Confirm Phase 1 exit criteria (50+ runs/day, >95% success)
- [ ] Merge `restructure/signal-mvp` into org `main`
