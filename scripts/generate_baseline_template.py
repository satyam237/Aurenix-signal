#!/usr/bin/env python3
"""Generate Week 0 baseline CSV template for manual ChatGPT + Gemini runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_PATH = ROOT / "data" / "prompts" / "nautikal_prompts.json"
OUTPUT_PATH = ROOT / "data" / "baseline" / "week0_baseline.csv"

ENGINES = ["chatgpt", "gemini"]
FIELDNAMES = [
    "prompt_id",
    "engine",
    "brand_mentioned",
    "rank_position",
    "response_snippet",
    "screenshot_path",
    "run_date",
    "notes",
]


def main() -> None:
    with PROMPTS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    for prompt in data["prompts"]:
        for engine in ENGINES:
            rows.append(
                {
                    "prompt_id": prompt["id"],
                    "engine": engine,
                    "brand_mentioned": "",
                    "rank_position": "",
                    "response_snippet": "",
                    "screenshot_path": "",
                    "run_date": "",
                    "notes": "",
                }
            )

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    print(
        "Fill in brand_mentioned (Y/N), rank_position, response_snippet, screenshot_path, run_date manually."
    )


if __name__ == "__main__":
    main()
