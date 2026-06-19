from __future__ import annotations

from datetime import datetime, timedelta, timezone

import streamlit as st

from shared.config import get_settings
from shared.supabase_client import get_supabase_client

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
else:
    st.info("No batches yet. Run: `python -m agents.prompt_runner.pipeline`")

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

st.caption(
    f"Daily cost cap: ${settings.daily_cost_cap_usd:.2f} | "
    f"Dedup window: {settings.dedup_hours}h | "
    f"Cron hour UTC: {settings.cron_hour_utc}"
)
