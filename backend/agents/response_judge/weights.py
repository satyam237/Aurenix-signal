"""Configurable GEO Score component weights (must sum to 1.0)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeoScoreWeights:
    brand_mentioned: float = 0.30
    mention_position: float = 0.25
    sentiment: float = 0.20
    factual_accuracy: float = 0.25

    def __post_init__(self) -> None:
        total = (
            self.brand_mentioned
            + self.mention_position
            + self.sentiment
            + self.factual_accuracy
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"GEO Score weights must sum to 1.0, got {total}")


DEFAULT_WEIGHTS = GeoScoreWeights()
