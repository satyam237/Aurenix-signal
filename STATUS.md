# Project Status — AureniX Signal

_Last updated: 2026-07-29_

> One-page snapshot. Details and checkboxes: [`PLAN.md`](PLAN.md). Setup: [`README.md`](README.md). Agents: [`AGENTS.md`](AGENTS.md).

## Where we are

**Phases 0–2 are complete for local production use.**  
The system can run prompts daily, score them into a GEO Score, and show ops + GEO metrics in Streamlit. **Phase 3 (full GEO product dashboard) is next.**

| | |
|--|--|
| **Product** | GEO platform — brand visibility in ChatGPT/Gemini answers |
| **Brand** | The Nautikal |
| **Branch** | `restructure/signal-mvp` (pushed to `org` + `origin`) |
| **Tests** | 39/39 mocked, passing |
| **Data store** | Supabase project live; migrations `001`–`003` applied |
| **Cron** | Local: `./scripts/run_daily_local.sh` · GCP: deferred |

## What is built

| Capability | How |
|------------|-----|
| Prompt execution | `backend/agents/prompt_runner` → OpenAI + Gemini → `raw_runs` |
| Scoring | `backend/agents/response_judge` PDF scorers → `scores` |
| GEO formula | 0.25 Inc + 0.25 Rank + 0.20 Acc + 0.15 Cit + 0.15 Sent |
| Ops + GEO UI | `dashboard/health_app.py` |
| Calibration | `scripts/calibrate_scores.py` → CSV for human QA |

## Phase board

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Foundation | Done | Week-0 manual UI baseline (T-02) still optional |
| 1 Prompt Runner | Done locally | T-06–T-09; GCP scheduler optional |
| 2 Response Judge | Done locally | T-10–T-15 |
| 3 GEO Dashboard | **Next** | T-16–T-19 |
| 4 Recommender | Not started | T-20–T-24 |

## How to run (operators)

```bash
source .venv/bin/activate
./scripts/run_daily_local.sh
streamlit run dashboard/health_app.py
```

## Next

1. Phase 3 GEO Dashboard (home, prompt table, response viewer)
2. Optional: finish human columns on latest calibration CSV
3. Optional: re-enable GCP Cloud Run cron when billing/access is stable
