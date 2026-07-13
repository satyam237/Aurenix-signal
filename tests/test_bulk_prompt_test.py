from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.bulk_prompt_test import run_bulk
from shared.concurrent_runner import PromptTask, TaskResult


def _mock_task_result(prompt_id: str, engine: str, sort_index: int) -> TaskResult:
    return TaskResult(
        task=PromptTask(
            prompt_id=prompt_id,
            category="high_intent",
            text=f"prompt {prompt_id}",
            engine=engine,
            sort_index=sort_index,
        ),
        status="success",
        model=f"mock-{engine}",
        tokens_in=10,
        tokens_out=50,
        cost_usd=0.002,
        response_text="response text",
        response_preview="response text",
        response_raw={"mock": True},
    )


@patch("scripts.bulk_prompt_test.run_tasks_concurrently")
@patch("scripts.bulk_prompt_test.build_adapters")
def test_run_bulk_output_schema(mock_build_adapters, mock_run_tasks, tmp_path: Path) -> None:
    mock_adapter = type("A", (), {"engine": "openai"})()
    mock_build_adapters.return_value = [mock_adapter]

    mock_run_tasks.return_value = [
        _mock_task_result("hi-01", "openai", 0),
        _mock_task_result("hi-01", "gemini", 1),
    ]

    output = tmp_path / "bulk_test.json"
    summary = run_bulk(limit=1, output=output, concurrency=2, sequential=False)

    assert summary["success_count"] == 2
    assert summary["failure_count"] == 0
    assert summary["concurrency"] == 2
    assert summary["prompt_count"] == 1
    assert summary["engine_count"] == 1

    assert output.exists()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "started_at" in data
    assert "finished_at" in data
    assert "results" in data
    assert len(data["results"]) == 2

    row = data["results"][0]
    assert row["prompt_id"] == "hi-01"
    assert row["engine"] == "openai"
    assert row["status"] == "success"
    assert "response_preview" in row
    assert "tokens_in" in row
    assert "cost_usd" in row


@patch("scripts.bulk_prompt_test.run_tasks_concurrently")
@patch("scripts.bulk_prompt_test.build_adapters")
def test_run_bulk_sequential_sets_concurrency_one(
    mock_build_adapters, mock_run_tasks, tmp_path: Path
) -> None:
    mock_adapter = type("A", (), {"engine": "openai"})()
    mock_build_adapters.return_value = [mock_adapter]
    mock_run_tasks.return_value = [_mock_task_result("hi-01", "openai", 0)]

    summary = run_bulk(limit=1, output=tmp_path / "out.json", concurrency=6, sequential=True)

    assert summary["concurrency"] == 1
    mock_run_tasks.assert_called_once()
    assert mock_run_tasks.call_args.kwargs["concurrency"] == 1
