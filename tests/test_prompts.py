from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_PATH = ROOT / "data" / "prompts" / "nautikal_prompts.json"


def test_prompt_library_has_25_prompts() -> None:
    with PROMPTS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["prompts"]) == 25


def test_prompt_categories() -> None:
    with PROMPTS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    categories = {}
    for p in data["prompts"]:
        categories[p["category"]] = categories.get(p["category"], 0) + 1
    assert categories["high_intent"] == 10
    assert categories["cruise_line_specific"] == 8
    assert categories["problem_use_case"] == 4
    assert categories["product_driven"] == 3
