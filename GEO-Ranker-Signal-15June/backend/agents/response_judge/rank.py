"""T-11 Rank scorer — list position + first-paragraph prominence.

If inclusion = 0, rank score = 0. Prominence bonus: first mention in first
paragraph = +10 (capped at 100).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from backend.agents.response_judge.inclusion import InclusionResult, score_inclusion
from backend.shared.brand_context import load_truth_registry


@dataclass(frozen=True)
class RankResult:
    score: int  # 0–100
    list_position: int | None  # 1 = first brand-like item in a list
    prominence_bonus: int
    details: dict[str, Any]


_LIST_ITEM = re.compile(
    r"(?:^|\n)\s*(?:[-*]|\d+[.)])\s+(.+?)(?=(?:\n\s*(?:[-*]|\d+[.)])|\n\n|\Z))",
    re.MULTILINE | re.DOTALL,
)


def _brand_needles(registry: dict[str, Any]) -> list[str]:
    aliases = list(registry.get("brand_aliases", []))
    brand = registry.get("brand_name")
    if brand and brand not in aliases:
        aliases = [brand, *aliases]
    for spec in registry.get("product_specs", {}).values():
        name = spec.get("name")
        if name:
            aliases.append(name)
    return [a for a in aliases if a]


def _contains_brand(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return any(n.lower() in lower for n in needles)


def score_rank(
    response_text: str,
    *,
    inclusion: InclusionResult | None = None,
    registry: dict[str, Any] | None = None,
) -> RankResult:
    registry = registry or load_truth_registry()
    inclusion = inclusion or score_inclusion(response_text, registry=registry)

    if inclusion.score == 0 or not inclusion.brand_mentioned:
        return RankResult(0, None, 0, {"reason": "inclusion_zero"})

    needles = _brand_needles(registry)
    items = [m.group(1).strip() for m in _LIST_ITEM.finditer(response_text)]
    list_position: int | None = None
    for i, item in enumerate(items, start=1):
        if _contains_brand(item, needles):
            list_position = i
            break

    if list_position is not None:
        # 1st → 100, 2nd → 80, 3rd → 60, … floor 20
        base = max(20, 100 - (list_position - 1) * 20)
    else:
        # No list: score from how early the mention appears (char offset)
        offset = inclusion.char_offset or 0
        denom = max(len(response_text) - 1, 1)
        early = 1.0 - (offset / denom)
        base = int(round(40 + early * 40))  # 40–80 range when not in a list

    first_para = response_text.split("\n\n", 1)[0]
    bonus = 10 if _contains_brand(first_para, needles) else 0
    score = min(100, base + bonus)
    return RankResult(
        score,
        list_position,
        bonus,
        {"base": base, "list_item_count": len(items)},
    )
