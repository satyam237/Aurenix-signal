from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.scheduler.cron_runner import should_run_now


def test_should_run_now_force() -> None:
    assert should_run_now(force=True) is True


def test_should_run_now_matches_hour() -> None:
    mock_settings = MagicMock()
    mock_settings.cron_hour_utc = datetime.now(timezone.utc).hour
    with patch("backend.scheduler.cron_runner.get_settings", return_value=mock_settings):
        assert should_run_now(force=False) is True


def test_cron_runner_main_force() -> None:
    with patch("backend.scheduler.cron_runner.run_pipeline") as mock_run:
        mock_run.return_value = "batch-123"
        from backend.scheduler import cron_runner

        assert cron_runner.main(force=True) == 0
        mock_run.assert_called_once()
