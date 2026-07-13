#!/usr/bin/env python3
"""Bulk-run prompts from local JSON against configured AI engines (no Supabase)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.prompt_runner.pipeline import build_adapters
from shared.brand_context import build_brand_system_prompt
from shared.concurrent_runner import (
    PromptTask,
    run_tasks_concurrently,
    task_result_to_bulk_row,
)
from shared.config import get_settings

PROMPTS_PATH = ROOT / "data" / "prompts" / "nautikal_prompts.json"
RUNS_DIR = ROOT / "data" / "runs"
CHECKPOINT_INTERVAL = 5

logger = logging.getLogger(__name__)


def load_prompts(limit: int | None = None) -> list[dict]:
    with PROMPTS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    prompts = data["prompts"]
    if limit is not None:
        prompts = prompts[:limit]
    return prompts


def _build_tasks(prompts: list[dict], engines: list[str]) -> list[PromptTask]:
    tasks: list[PromptTask] = []
    sort_index = 0
    for prompt in prompts:
        for engine in engines:
            tasks.append(
                PromptTask(
                    prompt_id=prompt["id"],
                    category=prompt.get("category"),
                    text=prompt["text"],
                    engine=engine,
                    sort_index=sort_index,
                )
            )
            sort_index += 1
    return tasks


def _write_checkpoint(
    checkpoint_path: Path,
    summary: dict,
    results: list[dict],
) -> None:
    partial = {**summary, "results": results, "checkpoint": True}
    checkpoint_path.write_text(json.dumps(partial, indent=2), encoding="utf-8")


def run_bulk(
    limit: int | None,
    output: Path | None,
    concurrency: int,
    sequential: bool,
    brand_context: bool = True,
) -> dict:
    settings = get_settings()
    if not settings.openai_api_key and not settings.gemini_api_key:
        raise ValueError(
            "No API keys configured. Copy .env.example to .env and add keys, "
            "then run: python scripts/check_ready.py"
        )

    adapters = build_adapters(settings)
    adapters_by_engine = {adapter.engine: adapter for adapter in adapters}
    prompts = load_prompts(limit)
    started_at = datetime.now(timezone.utc).isoformat()
    engines = list(adapters_by_engine.keys())
    tasks = _build_tasks(prompts, engines)

    effective_concurrency = 1 if sequential else concurrency
    system_prompt = build_brand_system_prompt() if brand_context else None

    logger.info(
        "Bulk test: %d prompts × %d engine(s), concurrency=%d, brand_context=%s",
        len(prompts),
        len(adapters),
        effective_concurrency,
        brand_context,
    )

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = output or RUNS_DIR / f"bulk_test_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    checkpoint_path = out_path.with_suffix(".partial.json")

    results: list[dict] = []
    success_count = 0
    failure_count = 0
    total_cost = 0.0

    base_summary = {
        "started_at": started_at,
        "prompt_count": len(prompts),
        "engine_count": len(adapters),
        "openai_model": settings.openai_model,
        "gemini_model": settings.gemini_model,
        "concurrency": effective_concurrency,
        "brand_context": brand_context,
    }

    def on_complete(result, completed: int, total: int) -> None:
        nonlocal success_count, failure_count, total_cost
        row = task_result_to_bulk_row(result)
        results.append(row)

        if result.status == "success":
            success_count += 1
            total_cost += result.cost_usd or 0
            logger.info(
                "Completed %d/%d (%.0f%%) — %s/%s OK — %d+%d tokens, $%.4f",
                completed,
                total,
                completed / total * 100,
                result.task.prompt_id,
                result.task.engine,
                result.tokens_in or 0,
                result.tokens_out or 0,
                result.cost_usd or 0,
            )
        else:
            failure_count += 1
            logger.error(
                "Completed %d/%d (%.0f%%) — %s/%s FAIL — %s",
                completed,
                total,
                completed / total * 100,
                result.task.prompt_id,
                result.task.engine,
                result.error,
            )

        if completed % CHECKPOINT_INTERVAL == 0:
            _write_checkpoint(
                checkpoint_path,
                {
                    **base_summary,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "total_cost_usd": round(total_cost, 6),
                },
                results,
            )

    task_results = run_tasks_concurrently(
        tasks,
        adapters_by_engine,
        concurrency=effective_concurrency,
        on_complete=on_complete,
        system=system_prompt,
    )

    # Ensure results are in sort order (callback order may differ under concurrency)
    task_results.sort(key=lambda r: r.task.sort_index)
    results = [task_result_to_bulk_row(r) for r in task_results]
    success_count = sum(1 for r in task_results if r.status == "success")
    failure_count = sum(1 for r in task_results if r.status == "failed")
    total_cost = sum(r.cost_usd or 0 for r in task_results if r.status == "success")

    summary = {
        **base_summary,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "success_count": success_count,
        "failure_count": failure_count,
        "total_cost_usd": round(total_cost, 6),
        "results": results,
    }

    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    summary["output_file"] = str(out_path)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk-test prompts against AI engines")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N prompts (e.g. --limit 3 for a quick smoke test)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: data/runs/bulk_test_<timestamp>.json)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Max parallel API calls (default: BULK_CONCURRENCY from .env or 6)",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run one API call at a time (old behavior, for debugging)",
    )
    parser.add_argument(
        "--no-brand-context",
        action="store_true",
        help="Skip the brand-grounding system prompt (neutral measurement mode)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = get_settings()
    concurrency = args.concurrency if args.concurrency is not None else settings.bulk_concurrency

    try:
        summary = run_bulk(
            args.limit,
            args.output,
            concurrency,
            args.sequential,
            brand_context=not args.no_brand_context,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("\n=== Bulk test complete ===")
    print(f"  Success: {summary['success_count']}")
    print(f"  Failed:  {summary['failure_count']}")
    print(f"  Cost:    ${summary['total_cost_usd']:.4f}")
    print(f"  Output:  {summary['output_file']}")

    return 0 if summary["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
