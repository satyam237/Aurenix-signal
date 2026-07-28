"""Score a single engine response into GEO Score components.

Brand mention + position use deterministic alias matching against the truth
registry. Sentiment and factual accuracy use an LLM judge (gpt-5-mini by
default) grounded in the same registry facts.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from backend.shared.brand_context import load_truth_registry
from backend.shared.config import Settings, get_settings
from backend.agents.response_judge.weights import DEFAULT_WEIGHTS, GeoScoreWeights

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are a GEO (AI Discovery Optimization) response judge.
Score how well an AI assistant response represents The Nautikal brand.

Return ONLY valid JSON with these keys:
- sentiment: number 0.0–1.0 (0=negative/hostile toward brand, 0.5=neutral/absent, 1.0=positive recommendation)
- factual_accuracy: number 0.0–1.0 (1.0=all brand claims match verified facts; 0.5=no brand claims; 0.0=contradicts verified facts or asserts disallowed claims)
- recommendation_rank: integer or null (1=first brand recommended, 2=second, …; null if brand not recommended)
- notes: short string explaining the scores

Use ONLY the verified facts and disallowed claims provided. Do not invent product details."""


@dataclass(frozen=True)
class BrandMention:
    mentioned: bool
    alias: str | None
    char_offset: int | None
    position_score: float | None  # 1.0 = mentioned at start, 0.0 = at end


@dataclass(frozen=True)
class JudgeResult:
    brand_mentioned: bool
    mention_position: float | None
    sentiment: float
    factual_accuracy: float
    geo_score: float
    judge_model: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_score_row(self, raw_run_id: str | None = None) -> dict[str, Any]:
        row: dict[str, Any] = {
            "brand_mentioned": self.brand_mentioned,
            "mention_position": self.mention_position,
            "sentiment": round(self.sentiment, 4),
            "factual_accuracy": round(self.factual_accuracy, 4),
            "geo_score": round(self.geo_score, 4),
            "judge_model": self.judge_model,
            "details": self.details,
        }
        if raw_run_id is not None:
            row["raw_run_id"] = raw_run_id
        return row


class LlmCompleter(Protocol):
    def complete(self, prompt: str, system: str | None = None) -> Any: ...


GEO_SCORE_WEIGHTS = DEFAULT_WEIGHTS


def detect_brand_mention(
    response_text: str,
    aliases: list[str] | None = None,
) -> BrandMention:
    """Find the earliest brand alias mention (case-insensitive)."""
    if not response_text.strip():
        return BrandMention(False, None, None, None)

    if aliases is None:
        registry = load_truth_registry()
        aliases = list(registry.get("brand_aliases", []))
        brand_name = registry.get("brand_name")
        if brand_name and brand_name not in aliases:
            aliases = [brand_name, *aliases]

    text_lower = response_text.lower()
    best: tuple[int, str] | None = None
    for alias in aliases:
        if not alias:
            continue
        idx = text_lower.find(alias.lower())
        if idx < 0:
            continue
        if best is None or idx < best[0]:
            best = (idx, alias)

    if best is None:
        return BrandMention(False, None, None, None)

    offset, alias = best
    # Earlier mentions score higher; empty text already handled.
    denom = max(len(response_text) - 1, 1)
    position_score = 1.0 - (offset / denom)
    return BrandMention(True, alias, offset, max(0.0, min(1.0, position_score)))


def compute_geo_score(
    *,
    brand_mentioned: bool,
    mention_position: float | None,
    sentiment: float,
    factual_accuracy: float,
    weights: GeoScoreWeights = DEFAULT_WEIGHTS,
) -> float:
    """Weighted composite in [0, 1]."""
    mention_component = 1.0 if brand_mentioned else 0.0
    position_component = mention_position if (brand_mentioned and mention_position is not None) else 0.0
    sentiment_c = _clamp01(sentiment)
    accuracy_c = _clamp01(factual_accuracy)
    score = (
        weights.brand_mentioned * mention_component
        + weights.mention_position * position_component
        + weights.sentiment * sentiment_c
        + weights.factual_accuracy * accuracy_c
    )
    return round(_clamp01(score), 4)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _build_judge_user_prompt(
    *,
    prompt_text: str,
    response_text: str,
    registry: dict[str, Any],
) -> str:
    claims = "\n".join(f"- {c}" for c in registry.get("approved_claims", []))
    disallowed = "\n".join(f"- {c}" for c in registry.get("disallowed_claims", []))
    return f"""BRAND: {registry.get("brand_name")} ({registry.get("website")})

VERIFIED FACTS:
{claims}

DISALLOWED CLAIMS (must score factual_accuracy near 0 if asserted):
{disallowed}

USER PROMPT:
{prompt_text}

AI RESPONSE:
{response_text}
"""


def _parse_llm_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _llm_soft_scores(
    *,
    prompt_text: str,
    response_text: str,
    registry: dict[str, Any],
    completer: LlmCompleter,
    model_name: str,
) -> tuple[float, float, dict[str, Any]]:
    user_prompt = _build_judge_user_prompt(
        prompt_text=prompt_text,
        response_text=response_text,
        registry=registry,
    )
    result = completer.complete(user_prompt, system=JUDGE_SYSTEM_PROMPT)
    raw_text = getattr(result, "text", "") or ""
    parsed = _parse_llm_json(raw_text)
    sentiment = _clamp01(float(parsed.get("sentiment", 0.5)))
    factual_accuracy = _clamp01(float(parsed.get("factual_accuracy", 0.5)))
    details = {
        "recommendation_rank": parsed.get("recommendation_rank"),
        "notes": parsed.get("notes", ""),
        "llm_tokens_in": getattr(result, "tokens_in", None),
        "llm_tokens_out": getattr(result, "tokens_out", None),
        "llm_cost_usd": getattr(result, "cost_usd", None),
        "judge_model": model_name,
    }
    return sentiment, factual_accuracy, details


def judge_response(
    *,
    response_text: str,
    prompt_text: str = "",
    completer: LlmCompleter | None = None,
    settings: Settings | None = None,
    weights: GeoScoreWeights = DEFAULT_WEIGHTS,
    registry: dict[str, Any] | None = None,
    skip_llm: bool = False,
) -> JudgeResult:
    """Score one response. When skip_llm=True, soft scores default to neutral 0.5."""
    cfg = settings or get_settings()
    registry = registry or load_truth_registry()
    aliases = list(registry.get("brand_aliases", []))

    mention = detect_brand_mention(response_text, aliases=aliases)
    model_name = "heuristic-only"

    if skip_llm or not response_text.strip():
        sentiment = 0.5
        factual_accuracy = 0.5
        details: dict[str, Any] = {
            "mode": "heuristic_only",
            "alias_matched": mention.alias,
            "char_offset": mention.char_offset,
        }
    else:
        if completer is None:
            from backend.agents.prompt_runner.adapters.openai_adapter import OpenAIAdapter

            completer = OpenAIAdapter(cfg)
        model_name = getattr(completer, "_model", cfg.openai_model)
        sentiment, factual_accuracy, llm_details = _llm_soft_scores(
            prompt_text=prompt_text,
            response_text=response_text,
            registry=registry,
            completer=completer,
            model_name=model_name,
        )
        details = {
            "mode": "llm_judge",
            "alias_matched": mention.alias,
            "char_offset": mention.char_offset,
            **llm_details,
        }

    geo = compute_geo_score(
        brand_mentioned=mention.mentioned,
        mention_position=mention.position_score,
        sentiment=sentiment,
        factual_accuracy=factual_accuracy,
        weights=weights,
    )
    return JudgeResult(
        brand_mentioned=mention.mentioned,
        mention_position=mention.position_score,
        sentiment=sentiment,
        factual_accuracy=factual_accuracy,
        geo_score=geo,
        judge_model=model_name,
        details=details,
    )


def judge_result_as_dict(result: JudgeResult) -> dict[str, Any]:
    return asdict(result)
