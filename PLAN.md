# PLAN.md — AureniX Signal Work Plan & Progress Log

> Living source of truth. Read at session start; update before ending.  
> Companions: [`STATUS.md`](STATUS.md) · [`AGENTS.md`](AGENTS.md) · [`README.md`](README.md) · [`docs/AureniX_Signal_Roadmap_Updated.pdf`](docs/AureniX_Signal_Roadmap_Updated.pdf)

---

## 1. Overview

| | |
|--|--|
| **What** | GEO: brand presence in AI answers → GEO Score → (later) content fixes |
| **Brand** | The Nautikal |
| **Stack** | Python · Supabase · OpenAI + Gemini · Streamlit · local cron |
| **Stage** | **Phases 0–2 done & on org `main` (PR #2)** · **Next = Phase 3** |
| **Branch** | `restructure/signal-mvp` (synced with merged work) |
| **Remotes** | `org` = The-Aurenix/aurenix-signal · `origin` = satyam237/Aurenix-signal |

**Pipeline:** prompts → `prompt_runner` → `raw_runs` → `response_judge` → `scores` → health/GEO panel.

**GEO:** `(0.25×I)+(0.25×R)+(0.20×A)+(0.15×C)+(0.15×S)`; Accuracy = % CORRECT; SoV by category.

## 2. Phase progress

### Phase 0 — Foundation ✅
- [x] Scaffold, truth registry, prompts, migrations 001–003
- [ ] T-02 Week-0 manual ChatGPT/Gemini UI baseline (human, optional)

### Phase 1 — Prompt Runner ✅
- [x] T-06 Adapters · T-07 Pipeline · T-08 Local cron · T-09 Health dashboard
- [ ] Optional GCP Cloud Run Scheduler

### Phase 1.5 — Concurrency & grounding ✅
- [x] Concurrent runner, rate limits, checkpoints, pricing, brand grounding

### Phase 2 — Response Judge ✅
- [x] T-10–T-15 scorers + composite/SoV · calibrate · GEO panel · **41 tests**
- [x] Accuracy = % CORRECT · health shows Avg GEO (SoV under by-category)

### Phase 3 — GEO Dashboard MVP ⏳ **NEXT**
- [ ] T-16 Home · T-17 Prompt table · T-18 Response viewer · T-19 Recommendations
- [ ] Drill-down: prompt + AI answer + scores (not in health app today)

### Phase 4 — Recommender ⏳
- [ ] T-20–T-24

## 3. Work log (compact)

### 2026-07-29 — Session wrap (PR #2 on org `main`)
- Phases 0–2 local path productionized; scoring QA (Accuracy % CORRECT, Avg GEO tile); docs; **41** tests.
- Pushed `restructure/signal-mvp`; **merged to org `main` via PR #2** (`011a15c`).
- Trello Done: T-06–T-15 (T-08 = local cron). Leave open: T-02, GCP cron, T-16+.
- Health app = ops + GEO rollups; **prompt/response viewer = Phase 3**.

### Earlier 2026-07-28–29
- Supabase live, Phase 2 scorers, local daily script; GCP deferred; packaging/docs rewrite.

## 4. Decisions

| Date | Decision |
|------|----------|
| 2026-07-29 | Accuracy = % CORRECT only; health Avg GEO (not duplicate SoV tile) |
| 2026-07-29 | Phases 0–2 = local production complete; GCP optional |
| 2026-07-29 | GEO weights PDF 0.25/0.25/0.20/0.15/0.15; Acc→Gemini, Sent→OpenAI |
| 2026-07-13 | `backend.` namespace + org skeleton |

## 5. Open items

- [ ] **Phase 3** T-16–T-19
- [ ] T-02 Week-0 manual baseline
- [ ] Human QA columns on calibration CSV
- [ ] GCP cron (optional)

## 6. Next session

1. Pull/sync `org/main` (or `restructure/signal-mvp`)
2. `pytest tests/ -q` (41)
3. Start **Phase 3** (prompt table + response viewer first)
4. End: update this file + `STATUS.md`
