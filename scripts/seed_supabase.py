#!/usr/bin/env python3
"""Seed Supabase prompts and brand_config from local JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from shared.config import get_settings
from shared.supabase_client import get_supabase_client

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_PATH = ROOT / "data" / "prompts" / "nautikal_prompts.json"
TRUTH_PATH = ROOT / "data" / "brands" / "nautikal_truth_registry.json"


def main() -> None:
    settings = get_settings()
    client = get_supabase_client(settings)

    with PROMPTS_PATH.open(encoding="utf-8") as f:
        prompts_data = json.load(f)

    brand_id = prompts_data["brand_id"]
    prompt_rows = [
        {
            "id": p["id"],
            "brand_id": brand_id,
            "text": p["text"],
            "category": p["category"],
            "intent_tag": p.get("intent_tag"),
            "active": True,
        }
        for p in prompts_data["prompts"]
    ]
    client.table("prompts").upsert(prompt_rows).execute()
    print(f"Upserted {len(prompt_rows)} prompts for brand '{brand_id}'")

    with TRUTH_PATH.open(encoding="utf-8") as f:
        truth_registry = json.load(f)

    client.table("brand_config").upsert(
        {
            "brand_id": brand_id,
            "truth_registry": truth_registry,
            "settings": {"seeded_from": str(TRUTH_PATH.name)},
        }
    ).execute()
    print(f"Upserted brand_config for '{brand_id}'")


if __name__ == "__main__":
    main()
