"""Orchestrate PDF-aligned scorers into a JudgeResult for persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from backend.agents.response_judge.accuracy import score_accuracy
from backend.agents.response_judge.citation import score_citation
from backend.agents.response_judge.composite import compute_geo_score
from backend.agents.response_judge.inclusion import score_inclusion
from backend.agents.response_judge.rank import score_rank
from backend.agents.response_judge.sentiment import score_sentiment
from backend.agents.response_judge.weights import DEFAULT_WEIGHTS, GeoScoreWeights
from backend.shared.brand_context import load_truth_registry
from backend.shared.config import Settings, get_settings

# Back-compat re-exports for older imports/tests
from backend.agents.response_judge.inclusion import InclusionResult  # noqa: F401


class LlmCompleter(Protocol):
    def complete(self, prompt: str, system: str | None = None) -> Any: ...


GEO_SCORE_WEIGHTS = DEFAULT_WEIGHTS


@dataclass(frozen=True)
class BrandMention:
    """Legacy shape used by older tests — derived from inclusion."""

    mentioned: bool
    alias: str | None
    char_offset: int | None
    position_score: float | None


@dataclass(frozen=True)
class JudgeResult:
    inclusion_score: int
    rank_score: int
    accuracy_score: int
    citation_score: int
    sentiment_score: int
    geo_score: float  # 0–100 PDF scale
    brand_mentioned: bool
    mention_position: float | None  # legacy 0–1 earlyness
    sentiment: float  # legacy 0–1
    factual_accuracy: float  # legacy 0–1
    judge_model: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_score_row(self, raw_run_id: str | None = None) -> dict[str, Any]:
        row: dict[str, Any] = {
            "inclusion_score": self.inclusion_score,
            "rank_score": self.rank_score,
            "accuracy_score": self.accuracy_score,
            "citation_score": self.citation_score,
            "sentiment_score": self.sentiment_score,
            "geo_score": round(self.geo_score / 100.0, 4),  # store 0–1 for existing column
            "brand_mentioned": self.brand_mentioned,
            "mention_position": self.mention_position,
            "sentiment": round(self.sentiment, 4),
            "factual_accuracy": round(self.factual_accuracy, 4),
            "judge_model": self.judge_model,
            "details": {
                **self.details,
                "geo_score_100": self.geo_score,
            },
        }
        if raw_run_id is not None:
            row["raw_run_id"] = raw_run_id
        return row


def detect_brand_mention(
    response_text: str,
    aliases: list[str] | None = None,
) -> BrandMention:
    """Back-compat wrapper around inclusion scorer."""
    registry = None
    if aliases is not None:
        registry = {
            "brand_aliases": aliases,
            "brand_name": aliases[0] if aliases else "",
            "product_specs": {},
        }
    inc = score_inclusion(response_text, registry=registry)
    position = None
    if inc.char_offset is not None and response_text:
        denom = max(len(response_text) - 1, 1)
        position = max(0.0, min(1.0, 1.0 - (inc.char_offset / denom)))
    return BrandMention(inc.brand_mentioned, inc.alias, inc.char_offset, position)


def judge_response(
    *,
    response_text: str,
    prompt_text: str = "",
    completer: LlmCompleter | None = None,
    accuracy_completer: LlmCompleter | None = None,
    sentiment_completer: LlmCompleter | None = None,
    settings: Settings | None = None,
    weights: GeoScoreWeights = DEFAULT_WEIGHTS,
    registry: dict[str, Any] | None = None,
    skip_llm: bool = False,
) -> JudgeResult:
    """Score one response with PDF component scorers."""
    cfg = settings or get_settings()
    registry = registry or load_truth_registry()

    inclusion = score_inclusion(response_text, registry=registry)
    rank = score_rank(response_text, inclusion=inclusion, registry=registry)
    citation = score_citation(response_text, registry=registry)

    acc_c = accuracy_completer
    sent_c = sentiment_completer
    model_name = "heuristic-only"

    if not skip_llm and response_text.strip():
        if completer is None and acc_c is None:
            # PDF prefers Gemini Flash for accuracy judge
            from backend.agents.prompt_runner.adapters.gemini_adapter import GeminiAdapter

            acc_c = GeminiAdapter(cfg)
        if sent_c is None:
            if completer is not None:
                sent_c = completer
            else:
                from backend.agents.prompt_runner.adapters.openai_adapter import OpenAIAdapter

                sent_c = OpenAIAdapter(cfg)
        if acc_c is None:
            acc_c = sent_c
        model_name = getattr(acc_c, "_model", None) or getattr(sent_c, "_model", cfg.gemini_model)

    accuracy = score_accuracy(
        response_text=response_text,
        prompt_text=prompt_text,
        completer=acc_c,
        registry=registry,
        skip_llm=skip_llm,
        brand_mentioned=inclusion.brand_mentioned,
    )
    sentiment = score_sentiment(
        response_text=response_text,
        prompt_text=prompt_text,
        completer=sent_c,
        skip_llm=skip_llm,
        brand_mentioned=inclusion.brand_mentioned,
    )

    composite = compute_geo_score(
        inclusion=inclusion.score,
        rank=rank.score,
        accuracy=accuracy.score,
        citation=citation.score,
        sentiment=sentiment.score,
        weights=weights,
    )

    mention_position = None
    if inclusion.char_offset is not None and response_text:
        denom = max(len(response_text) - 1, 1)
        mention_position = max(0.0, min(1.0, 1.0 - (inclusion.char_offset / denom)))

    details: dict[str, Any] = {
        "mode": "heuristic_only" if skip_llm else "llm_judge",
        "inclusion_tier": inclusion.tier,
        "alias_matched": inclusion.alias,
        "char_offset": inclusion.char_offset,
        "rank": {
            "list_position": rank.list_position,
            "prominence_bonus": rank.prominence_bonus,
            **rank.details,
        },
        "citation": {
            "urls": citation.urls,
            "owned": citation.owned,
            "earned": citation.earned,
            "third_party": citation.third_party,
        },
        "accuracy_claims": accuracy.claims,
        "accuracy_notes": accuracy.notes,
        "sentiment_framing": sentiment.framing,
        "sentiment_evidence": sentiment.evidence_phrases,
        "sentiment_notes": sentiment.notes,
        "weights": {
            "inclusion": weights.inclusion,
            "rank": weights.rank,
            "accuracy": weights.accuracy,
            "citation": weights.citation,
            "sentiment": weights.sentiment,
        },
    }

    return JudgeResult(
        inclusion_score=inclusion.score,
        rank_score=rank.score,
        accuracy_score=accuracy.score,
        citation_score=citation.score,
        sentiment_score=sentiment.score,
        geo_score=composite.geo_score,
        brand_mentioned=inclusion.brand_mentioned,
        mention_position=mention_position,
        sentiment=sentiment.score / 100.0,
        factual_accuracy=accuracy.score / 100.0,
        judge_model=model_name if not skip_llm else "heuristic-only",
        details=details,
    )


def judge_result_as_dict(result: JudgeResult) -> dict[str, Any]:
    return asdict(result)
