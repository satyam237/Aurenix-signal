"""Tests for PDF-aligned Response Judge scorers (all network mocked)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.agents.response_judge.citation import score_citation
from backend.agents.response_judge.composite import compute_geo_score, compute_share_of_voice
from backend.agents.response_judge.inclusion import score_inclusion
from backend.agents.response_judge.judge import detect_brand_mention, judge_response
from backend.agents.response_judge.pipeline import fetch_unscored_raw_runs, run_judge_pipeline
from backend.agents.response_judge.rank import score_rank
from backend.agents.response_judge.weights import DEFAULT_WEIGHTS, GeoScoreWeights


ALIASES = ["The Nautikal", "Nautikal", "thenautikal.com"]
REGISTRY = {
    "brand_name": "The Nautikal",
    "website": "https://www.thenautikal.com",
    "brand_aliases": ALIASES,
    "canonical_urls": ["https://www.thenautikal.com"],
    "product_specs": {
        "e7": {
            "name": "Cruise Essentials 7 Bundle",
            "url": "https://www.thenautikal.com/products/x",
        }
    },
    "approved_claims": ["The Nautikal sells cruise kits."],
    "disallowed_claims": [],
}


def test_inclusion_explicit() -> None:
    r = score_inclusion("I recommend The Nautikal kits.", registry=REGISTRY)
    assert r.score == 100
    assert r.tier == "explicit"
    assert r.brand_mentioned is True


def test_inclusion_indirect_product() -> None:
    r = score_inclusion("Try the Cruise Essentials 7 Bundle for cabins.", registry=REGISTRY)
    assert r.score == 50
    assert r.tier == "indirect"


def test_inclusion_absent() -> None:
    r = score_inclusion("Pack cubes and a power bank.", registry=REGISTRY)
    assert r.score == 0
    assert r.brand_mentioned is False


def test_rank_zero_when_no_inclusion() -> None:
    r = score_rank("No brand here.", registry=REGISTRY)
    assert r.score == 0


def test_rank_list_first_with_prominence() -> None:
    text = "Top picks for cruise kits:\n1. The Nautikal Essential 7\n2. Generic Brand Pack\n"
    r = score_rank(text, registry=REGISTRY)
    assert r.list_position == 1
    assert r.prominence_bonus == 10
    assert r.score == 100


def test_citation_owned_url() -> None:
    r = score_citation("See https://www.thenautikal.com/products/x for kits.", registry=REGISTRY)
    assert r.owned
    assert r.score >= 60


def test_citation_none() -> None:
    r = score_citation("No links here.", registry=REGISTRY)
    assert r.score == 0


def test_compute_geo_score_pdf_weights() -> None:
    perfect = compute_geo_score(inclusion=100, rank=100, accuracy=100, citation=100, sentiment=100)
    assert perfect.geo_score == 100.0
    assert perfect.geo_score_01 == 1.0

    partial = compute_geo_score(inclusion=0, rank=0, accuracy=50, citation=0, sentiment=50)
    # 0.20*50 + 0.15*50 = 10 + 7.5 = 17.5
    assert partial.geo_score == 17.5


def test_share_of_voice() -> None:
    rows = [
        {"inclusion_score": 100, "category": "high_intent"},
        {"inclusion_score": 0, "category": "high_intent"},
        {"inclusion_score": 50, "category": "problem"},
    ]
    sov = compute_share_of_voice(rows)
    assert sov["overall_sov"] == 66.67
    assert sov["by_category"]["high_intent"] == 50.0
    assert sov["by_category"]["problem"] == 100.0


def test_geo_score_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError):
        GeoScoreWeights(inclusion=0.5, rank=0.5, accuracy=0.5, citation=0.5, sentiment=0.5)


def test_default_weights_sum() -> None:
    w = DEFAULT_WEIGHTS
    assert abs(w.inclusion + w.rank + w.accuracy + w.citation + w.sentiment - 1.0) < 1e-9


def test_detect_brand_mention_found_early() -> None:
    text = "I recommend The Nautikal kits for cruise cabins. Other brands exist too."
    mention = detect_brand_mention(text, aliases=ALIASES)
    assert mention.mentioned is True
    assert mention.alias == "The Nautikal"
    assert mention.char_offset == 12


def test_judge_response_heuristic_only() -> None:
    text = "Try thenautikal.com for cruise essentials kits."
    result = judge_response(
        response_text=text, prompt_text="What to pack?", skip_llm=True, registry=REGISTRY
    )
    assert result.brand_mentioned is True
    assert result.inclusion_score == 100
    assert result.judge_model == "heuristic-only"
    assert 0.0 <= result.geo_score <= 100.0
    row = result.to_score_row(raw_run_id="run-1")
    assert row["raw_run_id"] == "run-1"
    assert row["inclusion_score"] == 100
    assert "geo_score" in row


def test_judge_response_with_mocked_llm() -> None:
    def _complete(prompt: str, system: str | None = None):
        sys = system or ""
        if "CORRECT" in sys or "factual accuracy" in sys.lower() or "Accuracy" in sys:
            text = '{"claims":[{"text":"kit","label":"CORRECT"}],"notes":"ok"}'
        else:
            text = '{"framing":"positive","evidence_phrases":["great kit"],"notes":"strong"}'
        return SimpleNamespace(text=text, tokens_in=10, tokens_out=20, cost_usd=0.001)

    completer = MagicMock()
    completer.complete.side_effect = _complete
    completer._model = "gemini-mock"

    result = judge_response(
        response_text="The Nautikal Essential 7 is a great cruise kit.",
        prompt_text="Best cruise accessories?",
        accuracy_completer=completer,
        sentiment_completer=completer,
        skip_llm=False,
        registry=REGISTRY,
    )
    assert result.brand_mentioned is True
    assert result.accuracy_score == 100
    assert result.sentiment_score == 100
    assert result.details["sentiment_framing"] == "positive"
    assert completer.complete.call_count == 2


def test_fetch_unscored_raw_runs_filters_scored() -> None:
    mock_client = MagicMock()
    runs_chain = (
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    )
    runs_chain.return_value.execute.return_value.data = [
        {"id": "a", "status": "success", "response_text": "x"},
        {"id": "b", "status": "success", "response_text": "y"},
    ]
    scores_table = MagicMock()
    scores_table.select.return_value.in_.return_value.execute.return_value.data = [
        {"raw_run_id": "a"}
    ]

    def table_side_effect(name: str):
        if name == "raw_runs":
            return mock_client.table.return_value
        return scores_table

    mock_client.table.side_effect = table_side_effect

    with patch(
        "backend.agents.response_judge.pipeline.get_supabase_client",
        return_value=mock_client,
    ):
        unscored = fetch_unscored_raw_runs(limit=10)
    assert len(unscored) == 1
    assert unscored[0]["id"] == "b"


def test_run_judge_pipeline_dry_run() -> None:
    run = {
        "id": "run-99",
        "prompt_id": "hi-01",
        "response_text": "Buy The Nautikal Ultimate 10 kit.",
        "status": "success",
    }
    with (
        patch(
            "backend.agents.response_judge.pipeline.fetch_unscored_raw_runs",
            return_value=[run],
        ),
        patch(
            "backend.agents.response_judge.pipeline._prompt_text_for_run",
            return_value="What kit?",
        ),
        patch(
            "backend.agents.response_judge.pipeline.get_supabase_client",
            return_value=MagicMock(),
        ),
    ):
        summary = run_judge_pipeline(limit=5, skip_llm=True, dry_run=True)

    assert summary["scored"] == 1
    assert summary["failures"] == 0
    assert summary["results"][0]["brand_mentioned"] is True
    assert summary["results"][0]["inclusion_score"] == 100
