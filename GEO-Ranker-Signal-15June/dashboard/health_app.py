from __future__ import annotations

from datetime import datetime, timedelta, timezone

import streamlit as st

from backend.agents.response_judge.composite import compute_share_of_voice
from backend.shared.config import get_settings
from backend.shared.supabase_client import get_supabase_client

st.set_page_config(page_title="Signal Health", page_icon="📡", layout="wide")
st.title("AureniX Signal — Prompt Runner Health")


@st.cache_resource
def _client():
    return get_supabase_client()


def _safe_client():
    try:
        return _client(), None
    except Exception as exc:
        return None, str(exc)


client, conn_error = _safe_client()
settings = get_settings()

if conn_error:
    st.error(f"Supabase not configured: {conn_error}")
    st.info("Copy `.env.example` to `.env` and set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY")
    st.stop()

col1, col2, col3, col4 = st.columns(4)

now = datetime.now(timezone.utc)
start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
week_ago = now - timedelta(days=7)

batches = (
    client.table("run_batches").select("*").order("started_at", desc=True).limit(10).execute().data
)

last_batch = batches[0] if batches else None

runs_today = (
    client.table("raw_runs")
    .select("id, status, cost_usd")
    .gte("created_at", start_of_day.isoformat())
    .execute()
    .data
)

runs_week = (
    client.table("raw_runs")
    .select("id, status, cost_usd")
    .gte("created_at", week_ago.isoformat())
    .execute()
    .data
)

success_today = sum(1 for r in runs_today if r["status"] == "success")
failed_today = sum(1 for r in runs_today if r["status"] == "failed")
cost_today = sum(float(r.get("cost_usd") or 0) for r in runs_today if r["status"] == "success")

week_total = len(runs_week)
week_success = sum(1 for r in runs_week if r["status"] == "success")
success_rate = (week_success / week_total * 100) if week_total else 0.0

target_daily = 50  # 25 prompts x 2 engines

with col1:
    st.metric("Last batch status", last_batch["status"] if last_batch else "—")
with col2:
    st.metric("Success rate (7d)", f"{success_rate:.1f}%")
with col3:
    st.metric("Runs today", f"{success_today + failed_today} / {target_daily}")
with col4:
    st.metric("Cost today", f"${cost_today:.4f}")

st.subheader("Last batch")
if last_batch:
    st.write(
        {
            "batch_id": last_batch["id"],
            "started_at": last_batch["started_at"],
            "finished_at": last_batch.get("finished_at"),
            "success": last_batch.get("success_count"),
            "failed": last_batch.get("failure_count"),
            "skipped": last_batch.get("skipped_count"),
            "cost_usd": last_batch.get("total_cost_usd"),
        }
    )
    st.caption(f"Last run timestamp: {last_batch.get('started_at')}")
else:
    st.info("No batches yet. Run: `python -m backend.agents.prompt_runner.pipeline`")

st.subheader("Recent batches")
if batches:
    st.dataframe(batches, use_container_width=True)
else:
    st.write("No batch history.")

st.subheader("Failure log (recent)")
failures = (
    client.table("raw_runs")
    .select("created_at, prompt_id, engine, model, error_message")
    .eq("status", "failed")
    .order("created_at", desc=True)
    .limit(20)
    .execute()
    .data
)
if failures:
    st.dataframe(failures, use_container_width=True)
else:
    st.success("No recent failures.")

# --- Phase 2 GEO scores panel (PDF DONE WHEN metrics) ---
st.divider()
st.header("GEO Scores (Phase 2)")

score_cols = (
    "id,raw_run_id,inclusion_score,rank_score,accuracy_score,citation_score,"
    "sentiment_score,geo_score,brand_mentioned,created_at,details"
)
try:
    scores = (
        client.table("scores")
        .select(score_cols)
        .order("created_at", desc=True)
        .limit(200)
        .execute()
        .data
        or []
    )
except Exception as exc:
    st.warning(
        f"Could not load Phase 2 score columns ({exc}). "
        "Apply `supabase/migrations/003_phase2_score_components.sql` in the SQL editor."
    )
    scores = []

if scores:
    prompts = {
        p["id"]: p for p in (client.table("prompts").select("id,category").execute().data or [])
    }
    runs_by_id = {
        r["id"]: r
        for r in (
            client.table("raw_runs")
            .select("id,prompt_id,engine")
            .in_("id", [s["raw_run_id"] for s in scores if s.get("raw_run_id")])
            .execute()
            .data
            or []
        )
    }

    enriched = []
    for s in scores:
        run = runs_by_id.get(s.get("raw_run_id") or "", {})
        pid = run.get("prompt_id")
        cat = (prompts.get(pid) or {}).get("category", "unknown")
        geo100 = (s.get("details") or {}).get("geo_score_100")
        if geo100 is None and s.get("geo_score") is not None:
            geo100 = float(s["geo_score"]) * 100
        enriched.append(
            {
                **s,
                "prompt_id": pid,
                "category": cat,
                "engine": run.get("engine"),
                "inclusion_score": s.get("inclusion_score") or 0,
                "geo_score_100": geo100,
            }
        )

    n = len(enriched)
    inclusion_pct = sum(1 for r in enriched if (r.get("inclusion_score") or 0) > 0) / n * 100
    avg_rank = sum(float(r.get("rank_score") or 0) for r in enriched) / n
    avg_acc = sum(float(r.get("accuracy_score") or 0) for r in enriched) / n
    geo_vals = [float(r["geo_score_100"]) for r in enriched if r.get("geo_score_100") is not None]
    avg_geo = sum(geo_vals) / len(geo_vals) if geo_vals else 0.0
    sov = compute_share_of_voice(enriched)

    # Inclusion % == overall SoV by definition (included / total). Show GEO composite instead of a duplicate.
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.metric("Inclusion %", f"{inclusion_pct:.1f}%")
    with g2:
        st.metric("Avg Rank (0–100)", f"{avg_rank:.1f}")
    with g3:
        st.metric("Avg Accuracy (0–100)", f"{avg_acc:.1f}")
    with g4:
        st.metric("Avg GEO Score (0–100)", f"{avg_geo:.1f}")

    st.caption(
        "GEO = 0.25×Inc + 0.25×Rank + 0.20×Acc + 0.15×Cit + 0.15×Sent. "
        f"Overall SoV = Inclusion % = {sov['overall_sov']:.1f}% "
        "(heuristic Accuracy defaults to 50 when scored with `--skip-llm`)."
    )

    st.subheader("SoV by category")
    st.json(sov.get("by_category") or {})

    st.subheader("Recent scores")
    display_cols = [
        "created_at",
        "prompt_id",
        "category",
        "engine",
        "inclusion_score",
        "rank_score",
        "accuracy_score",
        "citation_score",
        "sentiment_score",
        "geo_score_100",
        "brand_mentioned",
    ]
    st.dataframe(
        [{k: r.get(k) for k in display_cols} for r in enriched[:50]], use_container_width=True
    )
else:
    st.info(
        "No scores yet. Run: `python scripts/backfill_scores.py --supabase --skip-llm --rescore` "
        "or `./scripts/run_daily_local.sh --score-only`"
    )

st.caption(
    f"Daily cost cap: ${settings.daily_cost_cap_usd:.2f} | "
    f"Dedup window: {settings.dedup_hours}h | "
    f"Cron hour UTC: {settings.cron_hour_utc}"
)
