from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from backend.agents.prompt_runner.pipeline import run_pipeline
from backend.shared.config import get_settings

logger = logging.getLogger(__name__)


def should_run_now(force: bool = False) -> bool:
    if force:
        return True
    cfg = get_settings()
    now = datetime.now(timezone.utc)
    return now.hour == cfg.cron_hour_utc


def main(force: bool = False) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = get_settings()

    if not should_run_now(force):
        logger.info(
            "Skipping cron run — current UTC hour is not %d (use --force to override)",
            cfg.cron_hour_utc,
        )
        return 0

    logger.info("Starting scheduled prompt runner (cost cap $%.2f/day)", cfg.daily_cost_cap_usd)
    batch_id = run_pipeline(cfg)
    logger.info("Scheduled run complete: batch %s", batch_id)
    return 0


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    raise SystemExit(main(force=force_flag))
