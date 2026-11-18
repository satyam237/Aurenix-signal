# Project Status — AureniX Signal

_Last updated: 2026-07-29 (session closed)_

> Snapshot. Detail: [`PLAN.md`](PLAN.md). Setup: [`README.md`](README.md). Agents: [`AGENTS.md`](AGENTS.md).

## Where we are

**Phases 0–2 are complete, on org `main` (PR #2 merged).**  
Daily local run → score → Streamlit ops/GEO panel works. **Next session: Phase 3 GEO Dashboard.**

| | |
|--|--|
| **Product** | GEO — brand visibility in ChatGPT/Gemini answers |
| **Brand** | The Nautikal |
| **Git** | Org `main` includes latest QA (`8d3a243` via PR #2 `011a15c`); branch `restructure/signal-mvp` |
| **Tests** | 41/41 mocked, passing |
| **Supabase** | Live; migrations `001`–`003` |
| **Cron** | `./scripts/run_daily_local.sh` · GCP deferred |

## Built

| Capability | Notes |
|------------|--------|
| Prompt Runner | OpenAI + Gemini → `raw_runs` |
| Response Judge | PDF GEO 0.25/0.25/0.20/0.15/0.15; Accuracy = % CORRECT |
| Health UI | Inclusion %, Avg Rank/Accuracy/**GEO**; SoV by category |
| Not yet | Prompt text + AI response drill-down → **Phase 3** |

## Phase board

| Phase | Status |
|-------|--------|
| 0 Foundation | Done (T-02 optional) |
| 1 Prompt Runner | Done locally (T-06–T-09) |
| 2 Response Judge | Done (T-10–T-15) · **on main** |
| 3 GEO Dashboard | **Next** (T-16–T-19) |
| 4 Recommender | Not started |

## Run

```bash
source .venv/bin/activate
./scripts/run_daily_local.sh          # add --llm for real Accuracy/Sentiment
streamlit run dashboard/health_app.py
python -m pytest tests/ -q
```

## Next session

1. Phase 3: home + **prompt table** + **response viewer**
2. Optional: T-02 baseline / calibration human QA / GCP cron
