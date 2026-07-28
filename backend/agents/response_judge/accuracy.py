"""T-12 Accuracy checker — LLM-as-judge vs Truth Registry.

Classifies each AI claim about the brand as CORRECT / INCORRECT /
UNSUPPORTED / HALLUCINATED. Accuracy score = % CORRECT among brand claims
(or 50 when no brand claims).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.shared.brand_context import load_truth_registry

ACCURACY_SYSTEM = """You are a factual accuracy judge for brand claims in AI responses.
Return ONLY valid JSON:
{
  "claims": [{"text": "...", "label": "CORRECT|INCORRECT|UNSUPPORTED|HALLUCINATED"}],
  "notes": "short string"
}
Labels:
- CORRECT: matches verified facts
- INCORRECT: contradicts verified facts or asserts a disallowed claim
- UNSUPPORTED: about the brand but not in the registry (not clearly false)
- HALLUCINATED: invented specifics (prices, affiliations, guarantees) not in registry
If the response makes no claims about the brand, return {"claims": [], "notes": "no brand claims"}."""


@dataclass(frozen=True)
class AccuracyResult:
    score: int  # 0–100
    claims: list[dict[str, str]] = field(default_factory=list)
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


def _score_from_claims(claims: list[dict[str, str]]) -> int:
    if not claims:
        return 50
    labels = [str(c.get("label", "")).upper() for c in claims]
    correct = sum(1 for lab in labels if lab == "CORRECT")
    incorrect = sum(1 for lab in labels if lab in {"INCORRECT", "HALLUCINATED"})
    # Penalize incorrect/hallucinated heavily
    raw = (correct / len(labels)) * 100
    penalty = (incorrect / len(labels)) * 40
    return int(max(0, min(100, round(raw - penalty))))


def score_accuracy_heuristic(brand_mentioned: bool) -> AccuracyResult:
    """Neutral default when LLM is skipped."""
    return AccuracyResult(50 if brand_mentioned else 50, [], "heuristic_neutral", "heuristic-only")


def score_accuracy(
    *,
    response_text: str,
    prompt_text: str = "",
    completer: LlmCompleter | None = None,
    registry: dict[str, Any] | None = None,
    skip_llm: bool = False,
    brand_mentioned: bool = False,
) -> AccuracyResult:
    if skip_llm or completer is None or not response_text.strip():
        return score_accuracy_heuristic(brand_mentioned)

    registry = registry or load_truth_registry()
    claims_txt = "\n".join(f"- {c}" for c in registry.get("approved_claims", []))
    disallowed = "\n".join(f"- {c}" for c in registry.get("disallowed_claims", []))
    user = f"""BRAND: {registry.get("brand_name")} ({registry.get("website")})

VERIFIED FACTS:
{claims_txt}

DISALLOWED CLAIMS:
{disallowed}

USER PROMPT:
{prompt_text}

AI RESPONSE:
{response_text}
"""
    result = completer.complete(user, system=ACCURACY_SYSTEM)
    raw = getattr(result, "text", "") or ""
    parsed = _parse_json(raw)
    claims = list(parsed.get("claims") or [])
    model = getattr(completer, "_model", "llm")
    return AccuracyResult(
        score=_score_from_claims(claims),
        claims=claims,
        notes=str(parsed.get("notes", "")),
        judge_model=str(model),
    )
