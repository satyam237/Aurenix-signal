# Project Status — AureniX Signal

_Last updated: 2026-07-13 (evening)_

> Snapshot only. The living work plan, progress checkboxes, work log, and decisions are in [`PLAN.md`](PLAN.md) — update that file as work progresses.

## Summary

Phases 0–1 are **implemented**. Supabase + GCP cron **deployment assets are ready**; two manual steps remain before production runs land in `raw_runs`.

## Current state

| Item | Status |
|------|--------|
| Active branch | `restructure/signal-mvp` |
| Test suite | 23/23 passing |
| API keys in `.env` | OpenAI + Gemini + Supabase service role configured |
| Supabase schema on project `wjfxtmjjwezsamgiktzf` | **Not applied yet** — run SQL editor step |
| Supabase seeded | Blocked until schema applied |
| GCP cron deploy | **Assets ready** (`Dockerfile`, `deploy/gcp_deploy.sh`) — `gcloud` not installed locally |

## Immediate manual steps

1. **Apply Supabase schema** — `python scripts/apply_schema.py --print-sql` → paste migration in dashboard → `python scripts/setup_supabase.sh`
2. **Deploy GCP cron** — install gcloud, `export GCP_PROJECT_ID=...`, `./deploy/gcp_deploy.sh all`

## Phase progress

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Baseline, Truth Registry, Supabase schema, monorepo scaffold | ✅ Done (schema SQL ready; apply pending on live project) |
| 1 | Prompt Runner — automated daily runs → Supabase | ✅ Code done; production cron pending deploy |
| 2 | Response Judge + GEO Score | ⏳ Not started |
| 3 | GEO Dashboard MVP | ⏳ Not started |
| 4 | GEO Recommender + before/after loop | ⏳ Not started |

## What's new (Jul 13 evening)

- `scripts/apply_schema.py` — verify/apply schema (`--check-only`, `--apply`, `--print-sql`)
- `scripts/setup_supabase.sh` — one-shot seed + pipeline smoke test after schema
- `Dockerfile` + `.dockerignore` — container for cron runner
- `deploy/gcp_deploy.sh` + `deploy/README.md` — Cloud Run Jobs + Cloud Scheduler (free-tier path)
- Enhanced `scripts/verify_phase1.py` — checks all 5 Supabase tables

## Next steps

- [ ] Apply Supabase schema and run `scripts/setup_supabase.sh`
- [ ] Deploy GCP cron via `./deploy/gcp_deploy.sh all`
- [ ] Confirm Phase 1 exit criteria in production (50+ runs/day, >95% success)
- [ ] Merge `restructure/signal-mvp` into org `main`
- [ ] Begin Phase 2: Response Judge + GEO Score
