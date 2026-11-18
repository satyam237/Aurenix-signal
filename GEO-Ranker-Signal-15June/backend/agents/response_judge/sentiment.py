"""T-13 Sentiment scorer — LLM framing analysis with evidence phrases."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

SENTIMENT_SYSTEM = """You analyze how an AI response frames a brand (The Nautikal).
Return ONLY valid JSON:
{
  "framing": "positive|neutral|mixed|negative",
  "evidence_phrases": ["short quote", "..."],
  "notes": "short string"
}
If the brand is absent, use framing "neutral" and empty evidence_phrases."""

FRAMING_TO_SCORE = {
    "positive": 100,
    "neutral": 50,
    "mixed": 60,
    "negative": 15,
}


@dataclass(frozen=True)
class SentimentResult:
    score: int  # 0–100
    framing: str
    evidence_phrases: list[str] = field(default_factory=list)
    notes: str = ""
    judge_model: str = "heuristic-only"


class LlmCompleter(Protocol):
    def complete(self, prompt: str, system: str | None = None) -> Any: ...


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def score_sentiment_heuristic(brand_mentioned: bool) -> SentimentResult:
    framing = "neutral"
    return SentimentResult(50 if not brand_mentioned else 50, framing, [], "heuristic_neutral")


def score_sentiment(
    *,
    response_text: str,
    prompt_text: str = "",
    completer: LlmCompleter | None = None,
    skip_llm: bool = False,
    brand_mentioned: bool = False,
) -> SentimentResult:
    if skip_llm or completer is None or not response_text.strip():
        return score_sentiment_heuristic(brand_mentioned)

    user = f"""USER PROMPT:
{prompt_text}

AI RESPONSE:
{response_text}
"""
    result = completer.complete(user, system=SENTIMENT_SYSTEM)
    raw = getattr(result, "text", "") or ""
    parsed = _parse_json(raw)
    framing = str(parsed.get("framing", "neutral")).lower().strip()
    if framing not in FRAMING_TO_SCORE:
        framing = "neutral"
    evidence = [str(p) for p in (parsed.get("evidence_phrases") or [])][:8]
    model = getattr(completer, "_model", "llm")
    return SentimentResult(
        score=FRAMING_TO_SCORE[framing],
        framing=framing,
        evidence_phrases=evidence,
        notes=str(parsed.get("notes", "")),
        judge_model=str(model),
    )
