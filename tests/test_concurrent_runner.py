from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from shared.concurrent_runner import (
    PromptTask,
    TaskResult,
    run_tasks_concurrently,
    task_result_to_bulk_row,
)
from shared.models import NormalizedResponse


class SlowAdapter:
    def __init__(self, engine: str, delay: float = 0.2) -> None:
        self.engine = engine
        self._delay = delay
        self._model = f"mock-{engine}"
        self.concurrent_peak = 0
        self._active = 0
        self._lock = threading.Lock()

    def complete(self, prompt: str, system: str | None = None) -> NormalizedResponse:
        with self._lock:
            self._active += 1
            self.concurrent_peak = max(self.concurrent_peak, self._active)
        try:
            time.sleep(self._delay)
            return NormalizedResponse(
                text=f"{self.engine}:{prompt}",
                model=self._model,
                tokens_in=10,
                tokens_out=20,
                cost_usd=0.001,
                raw={"engine": self.engine},
            )
        finally:
            with self._lock:
                self._active -= 1


class FailingAdapter:
    engine = "fail"

    def complete(self, prompt: str, system: str | None = None) -> NormalizedResponse:
        raise RuntimeError("boom")


def _make_tasks(count: int, engine: str = "openai") -> list[PromptTask]:
    return [
        PromptTask(
            prompt_id=f"p-{i}",
            category="test",
            text=f"prompt {i}",
            engine=engine,
            sort_index=i,
        )
        for i in range(count)
    ]


def test_run_tasks_concurrently_faster_than_sequential() -> None:
    adapter = SlowAdapter("openai", delay=0.15)
    tasks = _make_tasks(6)

    start = time.monotonic()
    run_tasks_concurrently(tasks, {"openai": adapter}, concurrency=3)
    parallel_elapsed = time.monotonic() - start

    start = time.monotonic()
    run_tasks_concurrently(tasks, {"openai": adapter}, concurrency=1)
    serial_elapsed = time.monotonic() - start

    assert parallel_elapsed < serial_elapsed * 0.75


def test_results_preserve_sort_order() -> None:
    adapters = {
        "openai": SlowAdapter("openai", delay=0.01),
        "gemini": SlowAdapter("gemini", delay=0.01),
    }
    tasks = [
        PromptTask("a", "cat", "text a", "openai", 0),
        PromptTask("a", "cat", "text a", "gemini", 1),
        PromptTask("b", "cat", "text b", "openai", 2),
        PromptTask("b", "cat", "text b", "gemini", 3),
    ]

    results = run_tasks_concurrently(tasks, adapters, concurrency=4)

    assert [r.task.sort_index for r in results] == [0, 1, 2, 3]
    assert [r.task.prompt_id for r in results] == ["a", "a", "b", "b"]


def test_per_engine_semaphore_limits_parallelism() -> None:
    openai = SlowAdapter("openai", delay=0.1)
    gemini = SlowAdapter("gemini", delay=0.1)
    tasks = _make_tasks(3, "openai") + _make_tasks(3, "gemini")

    run_tasks_concurrently(tasks, {"openai": openai, "gemini": gemini}, concurrency=4)

    # concurrency=4, 2 engines => per_engine limit = 2
    assert openai.concurrent_peak <= 2
    assert gemini.concurrent_peak <= 2


def test_failure_does_not_block_other_tasks() -> None:
    ok_adapter = SlowAdapter("openai", delay=0.01)
    tasks = _make_tasks(2, "openai") + [
        PromptTask("bad", "cat", "x", "fail", 2),
    ]

    results = run_tasks_concurrently(
        tasks,
        {"openai": ok_adapter, "fail": FailingAdapter()},
        concurrency=3,
    )

    assert results[0].status == "success"
    assert results[1].status == "success"
    assert results[2].status == "failed"
    assert results[2].error == "boom"


def test_before_task_skips_when_false() -> None:
    adapter = SlowAdapter("openai", delay=0.01)
    tasks = _make_tasks(2)
    call_count = 0

    def before_task(_task: PromptTask) -> bool:
        nonlocal call_count
        call_count += 1
        return False

    results = run_tasks_concurrently(
        tasks, {"openai": adapter}, concurrency=2, before_task=before_task
    )

    assert all(r.status == "skipped" for r in results)
    assert call_count >= 2


def test_task_result_to_bulk_row_success() -> None:
    result = TaskResult(
        task=PromptTask("hi-01", "high_intent", "text", "openai", 0),
        status="success",
        model="gpt-5-mini",
        tokens_in=10,
        tokens_out=100,
        cost_usd=0.01,
        response_preview="preview text",
    )
    row = task_result_to_bulk_row(result)
    assert row["prompt_id"] == "hi-01"
    assert row["status"] == "success"
    assert row["model"] == "gpt-5-mini"
    assert row["response_preview"] == "preview text"


def test_task_result_to_bulk_row_failure() -> None:
    result = TaskResult(
        task=PromptTask("hi-01", "high_intent", "text", "gemini", 0),
        status="failed",
        error="timeout",
    )
    row = task_result_to_bulk_row(result)
    assert row["status"] == "failed"
    assert row["error"] == "timeout"


def test_empty_tasks_returns_empty() -> None:
    assert run_tasks_concurrently([], {"openai": MagicMock()}) == []
