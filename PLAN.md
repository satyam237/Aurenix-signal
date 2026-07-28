# PLAN.md — AureniX Signal Work Plan & Progress Log

> Living source of truth for progress. Read at session start; update before ending (checkboxes, work log, decisions).  
> Companions: [`STATUS.md`](STATUS.md) · [`AGENTS.md`](AGENTS.md) · [`README.md`](README.md) · roadmap [`docs/AureniX_Signal_Roadmap_Updated.pdf`](docs/AureniX_Signal_Roadmap_Updated.pdf)

---

## 1. Project overview

| | |
|--|--|
| **What** | GEO platform: measure brand presence in AI answers → GEO Score → (later) content recommendations |
| **Brand** | The Nautikal (thenautikal.com) |
| **Stack** | Python 3.11+ · Supabase · OpenAI + Gemini · Streamlit · local cron script |
| **Stage now** | **Phases 0–2 complete locally** · **Next = Phase 3 GEO Dashboard** |
| **Branch** | `restructure/signal-mvp` → org `main` |
| **Remotes** | `org` = The-Aurenix/aurenix-signal · `origin` = satyam237/Aurenix-signal |

**How (pipeline):** prompts → `prompt_runner` → `raw_runs` → `response_judge` scorers → `scores` → health/GEO Streamlit panel.

**GEO (PDF):** `(0.25×I)+(0.25×R)+(0.20×A)+(0.15×C)+(0.15×S)`; SoV by category.

## 2. Phase plan & progress

### Phase 0 — Foundation ✅
- [x] Scaffold, truth registry, 25 prompts (+ neutral), migrations 001–003, baseline CSV template
- [ ] T-02 Week-0 manual ChatGPT/Gemini UI baseline (human)

### Phase 1 — Prompt Runner ✅ (local)
- [x] T-06 Adapters · T-07 Pipeline · T-08 Local cron (`run_daily_local.sh`) · T-09 Health dashboard
- [ ] Optional GCP Cloud Run Scheduler

### Phase 1.5 — Concurrency & grounding ✅
- [x] Concurrent runner, rate limits, checkpoints, pricing, brand system prompts, bulk tests

### Phase 2 — Response Judge ✅ (local, PDF-aligned)
- [x] T-10–T-14 scorers + composite/SoV · T-15 calibrate script · GEO panel on health app · 41 tests
- [x] Accuracy = % CORRECT (no extra incorrect penalty) · health metrics show Avg GEO (not duplicate SoV tile)

### Phase 3 — GEO Dashboard MVP ⏳ NEXT
- [ ] T-16 Home (scores + trends) · T-17 Prompt table · T-18 Viewer · T-19 Recommendations tab
- [ ] Prompt + AI response + score drill-down lives here (not health app)

### Phase 4 — Recommender + loop ⏳
- [ ] T-20–T-24 gap detection, ICE backlog, execution kits, before/after, digest

## 3. Work log (newest first)

### 2026-07-29 — Scoring QA + PR for org main
- Verified GEO weights/formula; fixed Accuracy to pure % CORRECT; health panel shows Avg GEO; added rank/accuracy/geo storage tests (41).
- Docs updated; push `restructure/signal-mvp` + open PR for reviewer merge.

### 2026-07-29 — Docs + exoskeleton + Phase 2 push
- Rewrote README/STATUS/AGENTS/PLAN for stage clarity; added `requirements.txt`; hardened packaging/gitignore.
- Phase 2 PDF scorers already in tree; commit + push production-ready local path.

### 2026-07-29 — Close Phase 2 locally
- Discrete scorers, migration 003, local daily script, calibration CSV, GEO health panel.

### 2026-07-28 — Supabase live + early judge + GCP attempt
- Schema/seed/smoke; GCP project created; cron deferred in favor of local.

## 4. Decisions

| Date | Decision | Why |
|------|----------|-----|
| 2026-07-29 | Accuracy score = % CORRECT only | Matches scorer/PDF intent; drop extra incorrect penalty |
| 2026-07-29 | Health UI: Avg GEO tile; SoV kept under by-category | Inclusion % == overall SoV; avoid duplicate metric |
| 2026-07-29 | Docs treat Phases 0–2 as “local production complete” | Matches runnable path without GCP |
| 2026-07-29 | GEO weights = PDF 0.25/0.25/0.20/0.15/0.15 | Roadmap / Trello T-14 |
| 2026-07-29 | Accuracy → Gemini; sentiment → OpenAI | PDF T-12 |
| 2026-07-13 | `backend.` namespace + org skeleton | Merge into aurenix-signal |

## 5. Dependencies

- Install: `pip install -e ".[dev]"` or `pip install -r requirements.txt`
- Declared in [`pyproject.toml`](pyproject.toml); lock-free pins via `requirements.txt` mirrors

## 6. Open items

- [ ] Phase 3 T-16–T-19
- [ ] T-02 Week-0 manual baseline
- [ ] Human QA columns on calibration CSV
- [ ] GCP cron (optional)
- [ ] Merge `restructure/signal-mvp` → org `main`

## 7. Session checklist

1. Read this + `AGENTS.md`
2. Branch `restructure/signal-mvp`; `pytest tests/ -q` (41)
3. Prefer Phase 3 work unless directed otherwise
4. End: update §2–4 + `STATUS.md`
