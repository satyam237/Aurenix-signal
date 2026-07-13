from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from agents.prompt_runner.adapters.base import EngineAdapter
from shared.models import NormalizedResponse


@dataclass(frozen=True)
class PromptTask:
    prompt_id: str
    category: str | None
    text: str
    engine: str
    sort_index: int


@dataclass
class TaskResult:
    task: PromptTask
    status: str  # success | failed | skipped
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    response_text: str = ""
    response_preview: str = ""
    response_raw: dict | None = None
    error: str | None = None


def _per_engine_limit(concurrency: int, engine_count: int) -> int:
    if engine_count <= 0:
        return max(1, concurrency)
    return max(1, concurrency // engine_count)


def _run_single_task(
    task: PromptTask,
    adapter: EngineAdapter,
    engine_semaphore: threading.Semaphore,
    before_task: Callable[[PromptTask], bool] | None = None,
    system: str | None = None,
) -> TaskResult:
    if before_task is not None and not before_task(task):
        return TaskResult(task=task, status="skipped")

    with engine_semaphore:
        if before_task is not None and not before_task(task):
            return TaskResult(task=task, status="skipped")
        try:
            result: NormalizedResponse = adapter.complete(task.text, system=system)
            return TaskResult(
                task=task,
                status="success",
                model=result.model,
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                cost_usd=result.cost_usd,
                response_text=result.text,
                response_preview=result.text[:500],
                response_raw=result.raw,
            )
        except Exception as exc:
            return TaskResult(
                task=task,
                status="failed",
                model=getattr(adapter, "_model", "unknown"),
                error=str(exc),
            )


def run_tasks_concurrently(
    tasks: list[PromptTask],
    adapters_by_engine: dict[str, EngineAdapter],
    concurrency: int = 6,
    on_complete: Callable[[TaskResult, int, int], None] | None = None,
    before_task: Callable[[PromptTask], bool] | None = None,
    system: str | None = None,
) -> list[TaskResult]:
    """Run prompt tasks in parallel with per-engine concurrency limits."""
    if not tasks:
        return []

    if concurrency <= 1 or len(tasks) == 1:
        return _run_tasks_sequential(tasks, adapters_by_engine, on_complete, before_task, system)

    engine_count = len(adapters_by_engine)
    per_engine = _per_engine_limit(concurrency, engine_count)
    semaphores = {engine: threading.Semaphore(per_engine) for engine in adapters_by_engine}

    results: list[TaskResult | None] = [None] * len(tasks)
    total = len(tasks)
    completed_count = 0
    completed_lock = threading.Lock()

    def _handle_done(future, sort_index: int) -> None:
        nonlocal completed_count
        result = future.result()
        results[sort_index] = result
        with completed_lock:
            completed_count += 1
            count = completed_count
        if on_complete is not None:
            on_complete(result, count, total)

    with ThreadPoolExecutor(max_workers=min(concurrency, len(tasks))) as executor:
        futures = []
        for task in tasks:
            adapter = adapters_by_engine[task.engine]
            future = executor.submit(
                _run_single_task, task, adapter, semaphores[task.engine], before_task, system
            )
            future.add_done_callback(lambda f, idx=task.sort_index: _handle_done(f, idx))
            futures.append(future)

        for future in as_completed(futures):
            future.result()

    return [r for r in results if r is not None]


def _run_tasks_sequential(
    tasks: list[PromptTask],
    adapters_by_engine: dict[str, EngineAdapter],
    on_complete: Callable[[TaskResult, int, int], None] | None,
    before_task: Callable[[PromptTask], bool] | None = None,
    system: str | None = None,
) -> list[TaskResult]:
    results: list[TaskResult] = []
    total = len(tasks)
    for i, task in enumerate(tasks, start=1):
        adapter = adapters_by_engine[task.engine]
        sem = threading.Semaphore(1)
        result = _run_single_task(task, adapter, sem, before_task, system)
        results.append(result)
        if on_complete is not None:
            on_complete(result, i, total)
    return results


def task_result_to_bulk_row(result: TaskResult) -> dict:
    row: dict = {
        "prompt_id": result.task.prompt_id,
        "category": result.task.category,
        "engine": result.task.engine,
        "status": result.status,
    }
    if result.status == "success":
        row.update(
            {
                "model": result.model,
                "tokens_in": result.tokens_in,
                "tokens_out": result.tokens_out,
                "cost_usd": result.cost_usd,
                "response_preview": result.response_preview,
            }
        )
    else:
        row["error"] = result.error
    return row
