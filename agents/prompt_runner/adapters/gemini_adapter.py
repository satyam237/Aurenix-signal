from __future__ import annotations

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from agents.prompt_runner.adapters.base import EngineAdapter
from shared.config import Settings, get_settings
from shared.models import NormalizedResponse
from shared.pricing import estimate_cost_usd
from shared.rate_limiter import TokenBucketRateLimiter


class GeminiAdapter:
    engine = "gemini"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        genai.configure(api_key=self._settings.gemini_api_key)
        self._model = self._settings.gemini_model
        self._client = genai.GenerativeModel(self._model)
        self._limiter = TokenBucketRateLimiter(self._settings.rate_limit_rpm)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def complete(self, prompt: str) -> NormalizedResponse:
        self._limiter.acquire()
        response = self._client.generate_content(prompt)
        text = response.text or ""
        usage = response.usage_metadata
        tokens_in = usage.prompt_token_count if usage else 0
        tokens_out = usage.candidates_token_count if usage else 0
        raw = {
            "model": self._model,
            "text": text,
            "usage_metadata": {
                "prompt_token_count": tokens_in,
                "candidates_token_count": tokens_out,
            },
        }
        return NormalizedResponse(
            text=text,
            model=self._model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=estimate_cost_usd(self._model, tokens_in, tokens_out),
            raw=raw,
        )


def build_gemini_adapter(settings: Settings | None = None) -> EngineAdapter:
    return GeminiAdapter(settings)
