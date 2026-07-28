"""Configurable GEO Score component weights (must sum to 1.0).

Roadmap PDF MVP formula:
  0.25 Inclusion + 0.25 Rank + 0.20 Accuracy + 0.15 Citation + 0.15 Sentiment
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeoScoreWeights:
    inclusion: float = 0.25
    rank: float = 0.25
    accuracy: float = 0.20
    citation: float = 0.15
    sentiment: float = 0.15

    def __post_init__(self) -> None:
        total = self.inclusion + self.rank + self.accuracy + self.citation + self.sentiment
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"GEO Score weights must sum to 1.0, got {total}")


DEFAULT_WEIGHTS = GeoScoreWeights()
