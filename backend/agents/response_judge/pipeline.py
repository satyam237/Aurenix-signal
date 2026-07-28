"""Score unscored raw_runs rows and persist to the scores table."""

from __future__ import annotations

import logging
from typing import Any

from backend.agents.response_judge.judge import JudgeResult, judge_response
from backend.agents.response_judge.weights import DEFAULT_WEIGHTS, GeoScoreWeights
from backend.shared.config import Settings, get_settings
from backend.shared.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def fetch_unscored_raw_runs(
    *,
    limit: int = 100,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Return successful raw_runs that do not yet have a scores row."""
    client = get_supabase_client(settings)
    # Fetch recent successful runs, then filter out ones already scored.
    runs_resp = (
        client.table("raw_runs")
        .select("id,prompt_id,engine,model,response_text,status,created_at")
        .eq("status", "success")
        .order("created_at", desc=True)
        .limit(limit * 3)
        .execute()
    )
    runs = runs_resp.data or []
    if not runs:
        return []

    scored_resp = (
        client.table("scores")
        .select("raw_run_id")
        .in_("raw_run_id", [r["id"] for r in runs])
        .execute()
    )
    scored_ids = {row["raw_run_id"] for row in (scored_resp.data or [])}
    unscored = [r for r in runs if r["id"] not in scored_ids]
    return unscored[:limit]


def _prompt_text_for_run(client: Any, prompt_id: str | None) -> str:
    if not prompt_id:
        return ""
    resp = client.table("prompts").select("text").eq("id", prompt_id).limit(1).execute()
    rows = resp.data or []
    return rows[0]["text"] if rows else ""


def persist_score(result: JudgeResult, raw_run_id: str, settings: Settings | None = None) -> dict:
    client = get_supabase_client(settings)
    row = result.to_score_row(raw_run_id=raw_run_id)
    resp = client.table("scores").upsert(row, on_conflict="raw_run_id").execute()
    return (resp.data or [row])[0]


def score_raw_run(
    run: dict[str, Any],
    *,
    settings: Settings | None = None,
    weights: GeoScoreWeights = DEFAULT_WEIGHTS,
    skip_llm: bool = False,
    completer: Any = None,
) -> JudgeResult:
    client = get_supabase_client(settings)
    prompt_text = _prompt_text_for_run(client, run.get("prompt_id"))
    return judge_response(
        response_text=run.get("response_text") or "",
        prompt_text=prompt_text,
        settings=settings,
        weights=weights,
        skip_llm=skip_llm,
        completer=completer,
    )


def run_judge_pipeline(
    *,
    limit: int = 50,
    settings: Settings | None = None,
    weights: GeoScoreWeights = DEFAULT_WEIGHTS,
    skip_llm: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Score unscored raw_runs and upsert into scores."""
    cfg = settings or get_settings()
    runs = fetch_unscored_raw_runs(limit=limit, settings=cfg)
    scored = 0
    failures = 0
    results: list[dict[str, Any]] = []

    for run in runs:
        try:
            judgment = score_raw_run(
                run,
                settings=cfg,
                weights=weights,
                skip_llm=skip_llm,
            )
            if not dry_run:
                persist_score(judgment, run["id"], settings=cfg)
            scored += 1
            results.append(
                {
                    "raw_run_id": run["id"],
                    "prompt_id": run.get("prompt_id"),
                    "geo_score": judgment.geo_score,
                    "brand_mentioned": judgment.brand_mentioned,
                }
            )
        except Exception as exc:  # noqa: BLE001 — continue batch
            failures += 1
            logger.exception("Failed to score raw_run %s: %s", run.get("id"), exc)
            results.append({"raw_run_id": run.get("id"), "error": str(exc)})

    return {
        "candidates": len(runs),
        "scored": scored,
        "failures": failures,
        "dry_run": dry_run,
        "results": results,
    }
