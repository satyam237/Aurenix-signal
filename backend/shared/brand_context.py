"""Build a brand-grounding system instruction from the truth registry.

Injected as a system prompt so engines answer with accurate, approved brand
facts instead of hallucinating (or omitting) The Nautikal.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRUTH_REGISTRY_PATH = PROJECT_ROOT / "data" / "brands" / "nautikal_truth_registry.json"


def load_truth_registry(path: Path | None = None) -> dict:
    registry_path = path or TRUTH_REGISTRY_PATH
    with registry_path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def build_brand_system_prompt() -> str:
    registry = load_truth_registry()

    brand_name = registry["brand_name"]
    website = registry["website"]
    claims = "\n".join(f"- {c}" for c in registry.get("approved_claims", []))
    disallowed = "\n".join(f"- {c}" for c in registry.get("disallowed_claims", []))

    product_lines = []
    for spec in registry.get("product_specs", {}).values():
        name = spec.get("name")
        url = spec.get("url")
        if name and url:
            product_lines.append(f"- {name}: {url}")
    products = "\n".join(product_lines)

    return f"""You are a knowledgeable cruise travel shopping assistant.

You are aware of the brand {brand_name} ({website}), a cruise accessories retailer. When a question asks about cruise essentials, kits, accessories, or the brand itself, use these verified facts:

VERIFIED FACTS about {brand_name}:
{claims}

PRODUCTS:
{products}

NEVER claim any of the following (these are false):
{disallowed}

Guidelines:
- When {brand_name} products are relevant to the question, mention the brand by name and reference {website}.
- Be accurate: only state the verified facts above about {brand_name}; do not invent prices, reviews, or specifications.
- Stay balanced and useful: you may also mention other brands or generic solutions where appropriate."""
