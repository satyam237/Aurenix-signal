from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedResponse:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    raw: dict[str, Any]


@dataclass(frozen=True)
class PromptRecord:
    id: str
    brand_id: str
    text: str
    category: str
    intent_tag: str | None
    active: bool = True
