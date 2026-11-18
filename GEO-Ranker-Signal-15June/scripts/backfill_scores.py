#!/usr/bin/env python3
"""Backfill GEO scores for local bulk-run artifacts and/or Supabase raw_runs.

Examples:
  # Heuristic-only over local JSON (no API cost)
  python scripts/backfill_scores.py --local --skip-llm

  # Score unscored Supabase raw_runs with LLM judge
  python scripts/backfill_scores.py --supabase --limit 20

  # Both
  python scripts/backfill_scores.py --local --supabase --skip-llm --limit 50
"""

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

from backend.agents.response_judge.judge import judge_response
from backend.agents.response_judge.pipeline import run_judge_pipeline
from backend.shared.config import get_settings

RUNS_DIR = ROOT / "data" / "runs"
PROMPTS_PATH = ROOT / "data" / "prompts" / "nautikal_prompts.json"
OUTPUT_DIR = ROOT / "data" / "scores"

logger = logging.getLogger(__name__)


def _load_prompt_texts() -> dict[str, str]:
    with PROMPTS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return {p["id"]: p["text"] for p in data.get("prompts", [])}


def _response_text_from_row(row: dict) -> str:
    return (row.get("response_text") or row.get("response_preview") or "").strip()


def backfill_local(
    *,
    runs_dir: Path = RUNS_DIR,
    skip_llm: bool = True,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    prompt_texts = _load_prompt_texts()
    artifacts = sorted(runs_dir.glob("bulk_test_*.json"))
    scored_rows: list[dict] = []
    skipped = 0

    for path in artifacts:
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
        results = payload.get("results") or []
        for row in results:
            if row.get("status") != "success":
                skipped += 1
                continue
            text = _response_text_from_row(row)
            if not text:
                skipped += 1
                continue
            if limit is not None and len(scored_rows) >= limit:
                break
            judgment = judge_response(
                response_text=text,
                prompt_text=prompt_texts.get(row.get("prompt_id", ""), ""),
                skip_llm=skip_llm,
            )
            scored_rows.append(
                {
                    "source_file": path.name,
                    "prompt_id": row.get("prompt_id"),
                    "engine": row.get("engine"),
                    "model": row.get("model"),
                    **judgment.to_score_row(),
                }
            )
        if limit is not None and len(scored_rows) >= limit:
            break

    out_path = None
    if not dry_run and scored_rows:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = OUTPUT_DIR / f"backfill_local_{stamp}.json"
        out_path.write_text(
            json.dumps(
                {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "skip_llm": skip_llm,
                    "count": len(scored_rows),
                    "scores": scored_rows,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return {
        "mode": "local",
        "artifacts": len(artifacts),
        "scored": len(scored_rows),
        "skipped": skipped,
        "output": str(out_path) if out_path else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill GEO scores")
    parser.add_argument("--local", action="store_true", help="Score data/runs bulk JSON")
    parser.add_argument("--supabase", action="store_true", help="Score unscored raw_runs")
    parser.add_argument("--skip-llm", action="store_true", help="Heuristic-only (no API)")
    parser.add_argument("--rescore", action="store_true", help="Re-score even if scores row exists")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if not args.local and not args.supabase:
        parser.error("Pass --local and/or --supabase")

    summaries = []
    if args.local:
        summary = backfill_local(
            skip_llm=args.skip_llm,
            limit=args.limit,
            dry_run=args.dry_run,
        )
        summaries.append(summary)
        print(json.dumps(summary, indent=2))

    if args.supabase:
        get_settings()  # ensure .env loads / fails early
        summary = run_judge_pipeline(
            limit=args.limit,
            skip_llm=args.skip_llm,
            dry_run=args.dry_run,
            rescore=args.rescore,
        )
        summaries.append({"mode": "supabase", **summary})
        print(json.dumps(summaries[-1], indent=2, default=str))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
