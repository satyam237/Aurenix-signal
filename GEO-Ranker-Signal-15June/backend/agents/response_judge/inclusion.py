"""T-10 Inclusion scorer — fuzzy brand mention detection.

Score: 0 = absent, 50 = indirect, 100 = explicitly named.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from backend.shared.brand_context import load_truth_registry


@dataclass(frozen=True)
class InclusionResult:
    score: int  # 0 | 50 | 100
    tier: str  # absent | indirect | explicit
    alias: str | None
    char_offset: int | None
    brand_mentioned: bool


def _aliases_and_products(registry: dict[str, Any]) -> tuple[list[str], list[str]]:
    aliases = list(registry.get("brand_aliases", []))
    brand_name = registry.get("brand_name")
    if brand_name and brand_name not in aliases:
        aliases = [brand_name, *aliases]
    products: list[str] = []
    for spec in registry.get("product_specs", {}).values():
        name = spec.get("name")
        if name:
            products.append(name)
    return aliases, products


def _find_earliest(text_lower: str, needles: list[str]) -> tuple[int, str] | None:
    best: tuple[int, str] | None = None
    for needle in needles:
        if not needle:
            continue
        idx = text_lower.find(needle.lower())
        if idx < 0:
            continue
        if best is None or idx < best[0]:
            best = (idx, needle)
    return best


def score_inclusion(
    response_text: str,
    registry: dict[str, Any] | None = None,
) -> InclusionResult:
    """Return 0/50/100 inclusion score for a response."""
    if not response_text.strip():
        return InclusionResult(0, "absent", None, None, False)

    registry = registry or load_truth_registry()
    aliases, products = _aliases_and_products(registry)
    text_lower = response_text.lower()

    explicit = _find_earliest(text_lower, aliases)
    if explicit is not None:
        offset, alias = explicit
        return InclusionResult(100, "explicit", alias, offset, True)

    # Indirect: product names without brand alias, or loose "nautikal" stem
    product_hit = _find_earliest(text_lower, products)
    if product_hit is not None:
        offset, name = product_hit
        return InclusionResult(50, "indirect", name, offset, True)

    if re.search(r"\bnautikal\b", text_lower):
        idx = text_lower.find("nautikal")
        return InclusionResult(50, "indirect", "nautikal", idx, True)

    return InclusionResult(0, "absent", None, None, False)
