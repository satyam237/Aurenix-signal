from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from agents.prompt_runner.adapters.base import EngineAdapter
from agents.prompt_runner.adapters.gemini_adapter import build_gemini_adapter
from agents.prompt_runner.adapters.openai_adapter import build_openai_adapter
from shared.brand_context import build_brand_system_prompt
from shared.concurrent_runner import PromptTask, TaskResult, run_tasks_concurrently
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


def _build_pipeline_tasks(
    prompts: list[PromptRecord],
    adapters: list[EngineAdapter],
    cfg: Settings,
) -> tuple[list[PromptTask], int]:
    tasks: list[PromptTask] = []
    skipped_count = 0
    sort_index = 0
    for prompt in prompts:
        for adapter in adapters:
            if was_recently_run(prompt.id, adapter.engine, cfg.dedup_hours, cfg):
                skipped_count += 1
                logger.info("Skipping deduped run: %s / %s", prompt.id, adapter.engine)
                continue
            tasks.append(
                PromptTask(
                    prompt_id=prompt.id,
                    category=prompt.category,
                    text=prompt.text,
                    engine=adapter.engine,
                    sort_index=sort_index,
                )
            )
            sort_index += 1
    return tasks, skipped_count


def _insert_run_result(
    client: Any,
    batch_id: uuid.UUID,
    result: TaskResult,
) -> None:
    if result.status == "skipped":
        return

    if result.status == "success":
        client.table("raw_runs").insert(
            {
                "prompt_id": result.task.prompt_id,
                "engine": result.task.engine,
                "model": result.model,
                "response_text": result.response_text,
                "response_json": result.response_raw,
                "tokens_in": result.tokens_in,
                "tokens_out": result.tokens_out,
                "cost_usd": result.cost_usd,
                "status": "success",
                "run_batch_id": str(batch_id),
            }
        ).execute()
        return

    client.table("raw_runs").insert(
        {
            "prompt_id": result.task.prompt_id,
            "engine": result.task.engine,
            "model": result.model or "unknown",
            "response_text": "",
            "status": "failed",
            "error_message": result.error,
            "run_batch_id": str(batch_id),
        }
    ).execute()


def run_pipeline(settings: Settings | None = None, prompt_limit: int | None = None) -> uuid.UUID:
    cfg = settings or get_settings()
    client = get_supabase_client(cfg)
    adapters = build_adapters(cfg)
    adapters_by_engine = {adapter.engine: adapter for adapter in adapters}

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
    if prompt_limit is not None:
        prompts = prompts[:prompt_limit]

    daily_cost = get_daily_cost_so_far(cfg)
    tasks, skipped_count = _build_pipeline_tasks(prompts, adapters, cfg)

    cost_lock = threading.Lock()
    batch_cost = 0.0
    success_count = 0
    failure_count = 0
    cost_skipped_count = 0
    aborted = False
    abort_reason: str | None = None

    def _under_cost_cap() -> bool:
        nonlocal aborted, abort_reason
        with cost_lock:
            if daily_cost + batch_cost >= cfg.daily_cost_cap_usd:
                if not aborted:
                    aborted = True
                    abort_reason = f"Daily cost cap ${cfg.daily_cost_cap_usd:.2f} reached"
                    logger.warning(abort_reason)
                return False
            return True

    def before_task(_task: PromptTask) -> bool:
        return _under_cost_cap()

    logger.info(
        "Starting batch %s with %d tasks (%d skipped dedup) and %d engines",
        batch_id,
        len(tasks),
        skipped_count,
        len(adapters),
    )

    def on_complete(result: TaskResult, completed: int, total: int) -> None:
        nonlocal batch_cost, success_count, failure_count, cost_skipped_count

        if result.status == "skipped":
            with cost_lock:
                cost_skipped_count += 1
            return

        _insert_run_result(client, batch_id, result)

        with cost_lock:
            if result.status == "success":
                success_count += 1
                batch_cost += result.cost_usd or 0
                logger.info(
                    "Success [%d/%d]: %s / %s ($%.4f)",
                    completed,
                    total,
                    result.task.prompt_id,
                    result.task.engine,
                    result.cost_usd or 0,
                )
            else:
                failure_count += 1
                logger.error(
                    "Failed [%d/%d]: %s / %s — %s",
                    completed,
                    total,
                    result.task.prompt_id,
                    result.task.engine,
                    result.error,
                )

    run_tasks_concurrently(
        tasks,
        adapters_by_engine,
        concurrency=cfg.bulk_concurrency,
        on_complete=on_complete,
        before_task=before_task,
        system=build_brand_system_prompt(),
    )

    total_skipped = skipped_count + cost_skipped_count
    total_attempts = success_count + failure_count
    status = (
        "failed"
        if aborted
        else ("completed" if failure_count == 0 or success_count > 0 else "failed")
    )

    client.table("run_batches").update(
        {
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "total_prompts": total_attempts + total_skipped,
            "success_count": success_count,
            "failure_count": failure_count,
            "skipped_count": total_skipped,
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
        total_skipped,
        batch_cost,
    )
    return batch_id


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_pipeline()


def cli_main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run prompt pipeline against Supabase")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N active prompts (for testing)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_pipeline(prompt_limit=args.limit)


if __name__ == "__main__":
    cli_main()
