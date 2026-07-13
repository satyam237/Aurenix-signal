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


def test_all_prompts_are_brand_steered() -> None:
    with PROMPTS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    for p in data["prompts"]:
        assert "nautikal" in p["text"].lower(), f"{p['id']} is missing brand steering"


def test_neutral_prompt_backup_exists() -> None:
    neutral_path = PROMPTS_PATH.parent / "nautikal_prompts_neutral.json"
    assert neutral_path.exists()
    with neutral_path.open(encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["prompts"]) == 25


def test_brand_system_prompt_contents() -> None:
    from shared.brand_context import build_brand_system_prompt

    system = build_brand_system_prompt()
    assert "The Nautikal" in system
    assert "https://www.thenautikal.com" in system
    assert "NEVER claim" in system
    assert "Cruise Essentials 5" in system
