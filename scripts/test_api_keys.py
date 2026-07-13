#!/usr/bin/env python3
"""Smoke test OpenAI and Gemini API keys."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.prompt_runner.adapters.gemini_adapter import build_gemini_adapter
from agents.prompt_runner.adapters.openai_adapter import build_openai_adapter
from shared.config import get_settings

TEST_PROMPT = "Reply with exactly: API key OK"


def main() -> int:
    settings = get_settings()
    errors: list[str] = []

    if settings.openai_api_key:
        try:
            adapter = build_openai_adapter(settings)
            result = adapter.complete(TEST_PROMPT)
            print(f"OpenAI OK — model={result.model} tokens={result.tokens_in}+{result.tokens_out}")
        except Exception as exc:
            errors.append(f"OpenAI failed: {exc}")
    else:
        print("OpenAI skipped — OPENAI_API_KEY not set")

    if settings.gemini_api_key:
        try:
            adapter = build_gemini_adapter(settings)
            result = adapter.complete(TEST_PROMPT)
            print(f"Gemini OK — model={result.model} tokens={result.tokens_in}+{result.tokens_out}")
        except Exception as exc:
            errors.append(f"Gemini failed: {exc}")
    else:
        print("Gemini skipped — GEMINI_API_KEY not set")

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    if not settings.openai_api_key and not settings.gemini_api_key:
        print("No API keys configured — copy .env.example to .env and add keys", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
