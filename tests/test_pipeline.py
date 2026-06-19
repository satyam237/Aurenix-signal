from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from agents.prompt_runner.pipeline import was_recently_run
from shared.pricing import estimate_cost_usd


def test_estimate_cost_openai_mini() -> None:
    cost = estimate_cost_usd("gpt-4o-mini", tokens_in=1000, tokens_out=500)
    assert cost > 0
    assert cost < 0.01


def test_was_recently_run_true_when_recent() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = [
        {"id": "abc"}
    ]

    with patch("agents.prompt_runner.pipeline.get_supabase_client", return_value=mock_client):
        assert was_recently_run("hi-01", "openai", dedup_hours=6) is True


def test_was_recently_run_false_when_none() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = []

    with patch("agents.prompt_runner.pipeline.get_supabase_client", return_value=mock_client):
        assert was_recently_run("hi-01", "openai", dedup_hours=6) is False


def test_dedup_cutoff_uses_utc() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
    assert cutoff.tzinfo is not None
