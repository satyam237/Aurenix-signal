from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from agents.prompt_runner.adapters.base import EngineAdapter
from agents.prompt_runner.adapters.gemini_adapter import build_gemini_adapter
from agents.prompt_runner.adapters.openai_adapter import build_openai_adapter
from shared.config import Settings, get_settings
from shared.models import PromptRecord
from shared.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def _parse_prompt(row: dict[str, Any]) -> PromptRecord:
    return PromptRecord(
        id=row["id"],
        brand_id=row["brand_id"],
        text=row["text"],
        category=row["category"],
        intent_tag=row.get("intent_tag"),
        active=row.get("active", True),
    )


def load_active_prompts(brand_id: str, settings: Settings | None = None) -> list[PromptRecord]:
    client = get_supabase_client(settings)
    result = (
        client.table("prompts").select("*").eq("brand_id", brand_id).eq("active", True).execute()
    )
    return [_parse_prompt(row) for row in result.data]


def get_daily_cost_so_far(settings: Settings | None = None) -> float:
    client = get_supabase_client(settings)
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = (
        client.table("raw_runs")
        .select("cost_usd")
        .gte("created_at", start_of_day.isoformat())
        .eq("status", "success")
        .execute()
    )
    return sum(float(row.get("cost_usd") or 0) for row in result.data)


def was_recently_run(
    prompt_id: str,
    engine: str,
    dedup_hours: int,
    settings: Settings | None = None,
) -> bool:
    client = get_supabase_client(settings)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=dedup_hours)
    result = (
        client.table("raw_runs")
        .select("id")
        .eq("prompt_id", prompt_id)
        .eq("engine", engine)
        .eq("status", "success")
        .gte("created_at", cutoff.isoformat())
        .limit(1)
        .execute()
    )
    return len(result.data) > 0


def build_adapters(settings: Settings | None = None) -> list[EngineAdapter]:
    cfg = settings or get_settings()
    adapters: list[EngineAdapter] = []
    if cfg.openai_api_key:
        adapters.append(build_openai_adapter(cfg))
    if cfg.gemini_api_key:
        adapters.append(build_gemini_adapter(cfg))
    if not adapters:
        raise ValueError("At least one of OPENAI_API_KEY or GEMINI_API_KEY must be set")
    return adapters


def run_pipeline(settings: Settings | None = None) -> uuid.UUID:
    cfg = settings or get_settings()
    client = get_supabase_client(cfg)
    adapters = build_adapters(cfg)

    batch_id = uuid.uuid4()
    batch_row = {
        "id": str(batch_id),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "total_prompts": 0,
        "success_count": 0,
        "failure_count": 0,
        "skipped_count": 0,
        "total_cost_usd": 0,
    }
    client.table("run_batches").insert(batch_row).execute()

    prompts = load_active_prompts(cfg.brand_id, cfg)
    daily_cost = get_daily_cost_so_far(cfg)
    success_count = 0
    failure_count = 0
    skipped_count = 0
    batch_cost = 0.0
    aborted = False
    abort_reason: str | None = None

    logger.info(
        "Starting batch %s with %d prompts and %d engines", batch_id, len(prompts), len(adapters)
    )

    for prompt in prompts:
        for adapter in adapters:
            if daily_cost + batch_cost >= cfg.daily_cost_cap_usd:
                aborted = True
                abort_reason = f"Daily cost cap ${cfg.daily_cost_cap_usd:.2f} reached"
                logger.warning(abort_reason)
                break

            if was_recently_run(prompt.id, adapter.engine, cfg.dedup_hours, cfg):
                skipped_count += 1
                logger.info("Skipping deduped run: %s / %s", prompt.id, adapter.engine)
                continue

            try:
                result = adapter.complete(prompt.text)
                batch_cost += result.cost_usd
                client.table("raw_runs").insert(
                    {
                        "prompt_id": prompt.id,
                        "engine": adapter.engine,
                        "model": result.model,
                        "response_text": result.text,
                        "response_json": result.raw,
                        "tokens_in": result.tokens_in,
                        "tokens_out": result.tokens_out,
                        "cost_usd": result.cost_usd,
                        "status": "success",
                        "run_batch_id": str(batch_id),
                    }
                ).execute()
                success_count += 1
                logger.info("Success: %s / %s ($%.4f)", prompt.id, adapter.engine, result.cost_usd)
            except Exception as exc:
                failure_count += 1
                error_message = str(exc)
                logger.exception("Failed: %s / %s", prompt.id, adapter.engine)
                client.table("raw_runs").insert(
                    {
                        "prompt_id": prompt.id,
                        "engine": adapter.engine,
                        "model": getattr(adapter, "_model", "unknown"),
                        "response_text": "",
                        "status": "failed",
                        "error_message": error_message,
                        "run_batch_id": str(batch_id),
                    }
                ).execute()

        if aborted:
            break

    total_attempts = success_count + failure_count
    status = (
        "failed"
        if aborted
        else ("completed" if failure_count == 0 or success_count > 0 else "failed")
    )

    client.table("run_batches").update(
        {
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "total_prompts": total_attempts + skipped_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "skipped_count": skipped_count,
            "total_cost_usd": batch_cost,
            "status": status,
            "error_message": abort_reason,
        }
    ).eq("id", str(batch_id)).execute()

    logger.info(
        "Batch %s finished: success=%d failure=%d skipped=%d cost=$%.4f",
        batch_id,
        success_count,
        failure_count,
        skipped_count,
        batch_cost,
    )
    return batch_id


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_pipeline()


if __name__ == "__main__":
    main()
