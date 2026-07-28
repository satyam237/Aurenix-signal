# Project Status — AureniX Signal

_Last updated: 2026-07-28 (late)_

> Snapshot only. The living work plan, progress checkboxes, work log, and decisions are in [`PLAN.md`](PLAN.md) — update that file as work progresses.

## Summary

Phases 0–1 are **live**. Phase 2 Response Judge is **code-complete and scoring in Supabase**. GCP project `aurenix-signal-mvp` exists under `satyamj.work@gmail.com`; **billing must be linked** before Cloud Run cron deploy.

## Current state

| Item | Status |
|------|--------|
| Active branch | `restructure/signal-mvp` (pushed to org + origin) |
| Test suite | 32/32 passing |
| Supabase `wjfxtmjjwezsamgiktzf` | Live — schema 001+002, seeded, pipeline smoke OK |
| Scores table | 8/8 raw_runs scored (heuristic), avg GEO ~0.76 |
| GCP account | `satyamj.work@gmail.com` |
| GCP project | `aurenix-signal-mvp` |
| GCP billing | **Not linked** — blocks Cloud Run / Scheduler / Secret Manager |
| GCP cron | Pending billing → `./deploy/gcp_deploy.sh all` |

## Immediate manual step

1. Link billing on [aurenix-signal-mvp](https://console.cloud.google.com/billing/linkedaccount?project=aurenix-signal-mvp) (free trial / card required by GCP even for free-tier services).
2. Then: `export GCP_PROJECT_ID=aurenix-signal-mvp && ./deploy/gcp_deploy.sh all && ./deploy/gcp_deploy.sh run`

## Phase progress

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Baseline, Truth Registry, schema, scaffold | ✅ Done |
| 1 | Prompt Runner → Supabase | ✅ Live (cron pending billing) |
| 2 | Response Judge + GEO Score | ✅ Code + backfill done |
| 3 | GEO Dashboard MVP | ⏳ Next |
| 4 | GEO Recommender + before/after loop | ⏳ Not started |

## Next steps

- [ ] Link GCP billing → deploy + trigger cron once
- [ ] Confirm Phase 1 exit criteria after scheduled runs (50+/day, >95% success)
- [ ] Optional: LLM judge backfill (`python scripts/backfill_scores.py --supabase --limit 8`) — costs API
- [ ] Begin Phase 3: GEO Dashboard MVP
- [ ] Merge `restructure/signal-mvp` into org `main`
