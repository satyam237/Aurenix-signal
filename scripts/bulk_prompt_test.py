#!/usr/bin/env python3
"""Bulk-run prompts from local JSON against configured AI engines (no Supabase)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from agents.prompt_runner.pipeline import build_adapters
from shared.config import get_settings

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_PATH = ROOT / "data" / "prompts" / "nautikal_prompts.json"
RUNS_DIR = ROOT / "data" / "runs"

logger = logging.getLogger(__name__)


def load_prompts(limit: int | None = None) -> list[dict]:
    with PROMPTS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    prompts = data["prompts"]
    if limit is not None:
        prompts = prompts[:limit]
    return prompts


def run_bulk(limit: int | None, output: Path | None) -> dict:
    settings = get_settings()
    if not settings.openai_api_key and not settings.gemini_api_key:
        raise ValueError(
            "No API keys configured. Copy .env.example to .env and add keys, "
            "then run: python scripts/check_ready.py"
        )

    adapters = build_adapters(settings)
    prompts = load_prompts(limit)
    started_at = datetime.now(timezone.utc).isoformat()

    results: list[dict] = []
    success_count = 0
    failure_count = 0
    total_cost = 0.0

    logger.info(
        "Bulk test: %d prompts × %d engine(s)",
        len(prompts),
        len(adapters),
    )

    for i, prompt in enumerate(prompts, start=1):
        for adapter in adapters:
            prompt_id = prompt["id"]
            logger.info("[%d/%d] %s / %s", i, len(prompts), prompt_id, adapter.engine)
            row: dict = {
                "prompt_id": prompt_id,
                "category": prompt.get("category"),
                "engine": adapter.engine,
                "status": "failed",
            }
            try:
                result = adapter.complete(prompt["text"])
                row.update(
                    {
                        "status": "success",
                        "model": result.model,
                        "tokens_in": result.tokens_in,
                        "tokens_out": result.tokens_out,
                        "cost_usd": result.cost_usd,
                        "response_preview": result.text[:500],
                    }
                )
                success_count += 1
                total_cost += result.cost_usd
                logger.info(
                    "  OK — %d+%d tokens, $%.4f",
                    result.tokens_in,
                    result.tokens_out,
                    result.cost_usd,
                )
            except Exception as exc:
                row["error"] = str(exc)
                failure_count += 1
                logger.error("  FAIL — %s", exc)

            results.append(row)

    summary = {
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "prompt_count": len(prompts),
        "engine_count": len(adapters),
        "success_count": success_count,
        "failure_count": failure_count,
        "total_cost_usd": round(total_cost, 6),
        "openai_model": settings.openai_model,
        "gemini_model": settings.gemini_model,
        "results": results,
    }

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = output or RUNS_DIR / f"bulk_test_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
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
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    try:
        summary = run_bulk(args.limit, args.output)
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
