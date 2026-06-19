from __future__ import annotations

from typing import Protocol

from shared.models import NormalizedResponse


class EngineAdapter(Protocol):
    engine: str

    def complete(self, prompt: str) -> NormalizedResponse: ...
