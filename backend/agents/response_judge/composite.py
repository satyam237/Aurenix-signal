"""T-14 Composite GEO Score + Share-of-Voice rollups.

MVP formula (roadmap PDF):
  (0.25 × Inclusion) + (0.25 × Rank) + (0.20 × Accuracy)
  + (0.15 × Citation) + (0.15 × Sentiment)

All component inputs are on a 0–100 scale; geo_score is returned 0–100
(also available as 0–1 via geo_score_01).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from backend.agents.response_judge.weights import DEFAULT_WEIGHTS, GeoScoreWeights


@dataclass(frozen=True)
class CompositeResult:
    geo_score: float  # 0–100
    geo_score_01: float  # 0–1 for legacy column convenience


def compute_geo_score(
    *,
    inclusion: float,
    rank: float,
    accuracy: float,
    citation: float,
    sentiment: float,
    weights: GeoScoreWeights = DEFAULT_WEIGHTS,
) -> CompositeResult:
    score = (
        weights.inclusion * float(inclusion)
        + weights.rank * float(rank)
        + weights.accuracy * float(accuracy)
        + weights.citation * float(citation)
        + weights.sentiment * float(sentiment)
    )
    score = max(0.0, min(100.0, score))
    return CompositeResult(round(score, 2), round(score / 100.0, 4))


def compute_share_of_voice(
    rows: Iterable[dict[str, Any]],
    *,
    inclusion_key: str = "inclusion_score",
    category_key: str = "category",
) -> dict[str, Any]:
    """SoV = brand-included prompts / total scored prompts × 100 (overall + by category)."""
    by_cat: dict[str, list[bool]] = defaultdict(list)
    overall: list[bool] = []
    for row in rows:
        included = float(row.get(inclusion_key) or 0) > 0
        overall.append(included)
        cat = str(row.get(category_key) or "unknown")
        by_cat[cat].append(included)

    def _pct(flags: list[bool]) -> float:
        if not flags:
            return 0.0
        return round(100.0 * sum(1 for f in flags if f) / len(flags), 2)

    return {
        "overall_sov": _pct(overall),
        "total": len(overall),
        "included": sum(1 for f in overall if f),
        "by_category": {cat: _pct(flags) for cat, flags in sorted(by_cat.items())},
    }
