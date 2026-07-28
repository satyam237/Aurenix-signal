#!/usr/bin/env python3
"""T-15 Manual QA / calibration helper for GEO scores.

Samples scored (or freshly judged) responses into a CSV for human review,
and prints a summary of judge outputs for calibration.

Examples:
  python scripts/calibrate_scores.py --limit 25 --skip-llm
  python scripts/calibrate_scores.py --from-supabase --limit 25
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.agents.response_judge.composite import compute_share_of_voice
from backend.agents.response_judge.judge import judge_response
from backend.agents.response_judge.pipeline import fetch_unscored_raw_runs, persist_score
from backend.shared.config import get_settings
from backend.shared.supabase_client import get_supabase_client

PROMPTS_PATH = ROOT / "data" / "prompts" / "nautikal_prompts.json"
OUT_DIR = ROOT / "data" / "scores"


def _prompt_meta() -> dict[str, dict]:
    with PROMPTS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return {p["id"]: p for p in data.get("prompts", [])}


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate GEO scores (T-15)")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--skip-llm", action="store_true", default=True)
    parser.add_argument("--llm", action="store_true", help="Use LLM judges (costs API)")
    parser.add_argument("--from-supabase", action="store_true", default=True)
    parser.add_argument("--persist", action="store_true", help="Upsert scores to Supabase")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    skip_llm = not args.llm

    get_settings()
    meta = _prompt_meta()
    runs = fetch_unscored_raw_runs(limit=args.limit, rescore=True)
    if not runs:
        print("No successful raw_runs found.")
        return 1

    client = get_supabase_client()
    rows_out: list[dict] = []
    for run in runs:
        pid = run.get("prompt_id")
        pmeta = meta.get(pid or "", {})
        prompt_text = pmeta.get("text", "")
        if not prompt_text and pid:
            resp = client.table("prompts").select("text,category").eq("id", pid).limit(1).execute()
            if resp.data:
                prompt_text = resp.data[0].get("text") or ""
                pmeta = {**pmeta, **resp.data[0]}

        judgment = judge_response(
            response_text=run.get("response_text") or "",
            prompt_text=prompt_text,
            skip_llm=skip_llm,
        )
        if args.persist and not args.dry_run:
            persist_score(judgment, run["id"])

        rows_out.append(
            {
                "raw_run_id": run["id"],
                "prompt_id": pid,
                "category": pmeta.get("category", ""),
                "engine": run.get("engine"),
                "inclusion_score": judgment.inclusion_score,
                "rank_score": judgment.rank_score,
                "accuracy_score": judgment.accuracy_score,
                "citation_score": judgment.citation_score,
                "sentiment_score": judgment.sentiment_score,
                "geo_score_100": judgment.geo_score,
                "brand_mentioned": judgment.brand_mentioned,
                "sentiment_framing": judgment.details.get("sentiment_framing"),
                "human_inclusion": "",  # fill manually
                "human_rank": "",
                "human_notes": "",
                "response_preview": (run.get("response_text") or "")[:400],
            }
        )

    sov = compute_share_of_voice(rows_out)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_path = OUT_DIR / f"calibration_{stamp}.csv"
    json_path = OUT_DIR / f"calibration_{stamp}.json"

    if not args.dry_run:
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
            writer.writeheader()
            writer.writerows(rows_out)
        json_path.write_text(
            json.dumps({"sov": sov, "count": len(rows_out), "rows": rows_out}, indent=2),
            encoding="utf-8",
        )

    avg_inc = sum(r["inclusion_score"] for r in rows_out) / len(rows_out)
    avg_rank = sum(r["rank_score"] for r in rows_out) / len(rows_out)
    avg_acc = sum(r["accuracy_score"] for r in rows_out) / len(rows_out)
    print(
        json.dumps(
            {
                "sampled": len(rows_out),
                "avg_inclusion": round(avg_inc, 2),
                "avg_rank": round(avg_rank, 2),
                "avg_accuracy": round(avg_acc, 2),
                "sov": sov,
                "csv": str(csv_path) if not args.dry_run else None,
                "json": str(json_path) if not args.dry_run else None,
                "note": "Fill human_* columns in the CSV, then compare to judge columns.",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
