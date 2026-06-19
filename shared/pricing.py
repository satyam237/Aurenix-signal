from __future__ import annotations

# USD per 1M tokens (input, output) — update as provider pricing changes
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
}


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    input_rate, output_rate = MODEL_PRICING.get(model, (0.50, 1.50))
    return (tokens_in * input_rate + tokens_out * output_rate) / 1_000_000
