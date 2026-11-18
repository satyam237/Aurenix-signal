"""T-13 Citation scorer — extract URLs and classify owned / earned / third-party."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from backend.shared.brand_context import load_truth_registry

_URL_RE = re.compile(r"https?://[^\s\)\]\>\"']+", re.IGNORECASE)


@dataclass(frozen=True)
class CitationResult:
    score: int  # 0–100
    urls: list[str] = field(default_factory=list)
    owned: list[str] = field(default_factory=list)
    earned: list[str] = field(default_factory=list)
    third_party: list[str] = field(default_factory=list)


def _owned_hosts(registry: dict[str, Any]) -> set[str]:
    hosts: set[str] = set()
    website = registry.get("website") or ""
    for raw in [website, *registry.get("canonical_urls", [])]:
        try:
            host = urlparse(raw if "://" in raw else f"https://{raw}").netloc.lower()
        except Exception:  # noqa: BLE001
            continue
        host = host.removeprefix("www.")
        if host:
            hosts.add(host)
    hosts.add("thenautikal.com")
    return hosts


def _classify(url: str, owned: set[str]) -> str:
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:  # noqa: BLE001
        return "third_party"
    if any(host == o or host.endswith("." + o) for o in owned):
        return "owned"
    # Earned: review/press/blog domains (heuristic allowlist)
    earned_hints = (
        "reddit.com",
        "tripadvisor.com",
        "cruise.com",
        "cruisecritic.com",
        "youtube.com",
        "medium.com",
        "forbes.com",
        "nytimes.com",
    )
    if any(host == h or host.endswith("." + h) for h in earned_hints):
        return "earned"
    return "third_party"


def score_citation(
    response_text: str,
    registry: dict[str, Any] | None = None,
) -> CitationResult:
    registry = registry or load_truth_registry()
    owned_hosts = _owned_hosts(registry)
    raw_urls = [u.rstrip(".,;") for u in _URL_RE.findall(response_text or "")]
    # de-dupe preserve order
    seen: set[str] = set()
    urls: list[str] = []
    for u in raw_urls:
        if u not in seen:
            seen.add(u)
            urls.append(u)

    owned: list[str] = []
    earned: list[str] = []
    third: list[str] = []
    for u in urls:
        kind = _classify(u, owned_hosts)
        if kind == "owned":
            owned.append(u)
        elif kind == "earned":
            earned.append(u)
        else:
            third.append(u)

    if not urls:
        score = 0
    else:
        # Owned citations weigh most; mix of types still scores well
        score = min(
            100,
            len(owned) * 50 + len(earned) * 25 + len(third) * 10,
        )
        if owned and not third:
            score = max(score, 80)
        if owned:
            score = max(score, 60)

    return CitationResult(score, urls, owned, earned, third)
