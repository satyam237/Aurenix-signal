from __future__ import annotations

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from agents.prompt_runner.adapters.base import EngineAdapter
from shared.config import Settings, get_settings
from shared.models import NormalizedResponse
from shared.pricing import estimate_cost_usd
from shared.rate_limiter import TokenBucketRateLimiter


class OpenAIAdapter:
    engine = "openai"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        self._client = OpenAI(api_key=self._settings.openai_api_key)
        self._model = self._settings.openai_model
        self._limiter = TokenBucketRateLimiter(self._settings.rate_limit_rpm)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def complete(self, prompt: str, system: str | None = None) -> NormalizedResponse:
        self._limiter.acquire()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        choice = response.choices[0]
        text = choice.message.content or ""
        usage = response.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0
        raw = response.model_dump(mode="json")
        return NormalizedResponse(
            text=text,
            model=self._model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=estimate_cost_usd(self._model, tokens_in, tokens_out),
            raw=raw,
        )


def build_openai_adapter(settings: Settings | None = None) -> EngineAdapter:
    return OpenAIAdapter(settings)
