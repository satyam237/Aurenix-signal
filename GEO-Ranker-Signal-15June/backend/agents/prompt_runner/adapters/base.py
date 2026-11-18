from __future__ import annotations

from typing import Protocol

from backend.shared.models import NormalizedResponse


class EngineAdapter(Protocol):
    engine: str

    def complete(self, prompt: str, system: str | None = None) -> NormalizedResponse: ...
