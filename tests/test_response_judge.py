"""Tests for Response Judge + GEO Score (all network mocked)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.agents.response_judge.judge import (
    compute_geo_score,
    detect_brand_mention,
    judge_response,
)
from backend.agents.response_judge.pipeline import fetch_unscored_raw_runs, run_judge_pipeline
from backend.agents.response_judge.weights import DEFAULT_WEIGHTS, GeoScoreWeights


ALIASES = ["The Nautikal", "Nautikal", "thenautikal.com"]


def test_detect_brand_mention_found_early() -> None:
    text = "I recommend The Nautikal kits for cruise cabins. Other brands exist too."
    mention = detect_brand_mention(text, aliases=ALIASES)
    assert mention.mentioned is True
    assert mention.alias == "The Nautikal"
    assert mention.char_offset == 12  # len("I recommend ")
    assert mention.position_score is not None
    assert mention.position_score > 0.7


def test_detect_brand_mention_absent() -> None:
    text = "Pack cubes, a power bank, and magnetic hooks from generic stores."
    mention = detect_brand_mention(text, aliases=ALIASES)
    assert mention.mentioned is False
    assert mention.position_score is None


def test_compute_geo_score_weights() -> None:
    # Full marks on every component
    perfect = compute_geo_score(
        brand_mentioned=True,
        mention_position=1.0,
        sentiment=1.0,
        factual_accuracy=1.0,
    )
    assert perfect == 1.0

    none = compute_geo_score(
        brand_mentioned=False,
        mention_position=None,
        sentiment=0.5,
        factual_accuracy=0.5,
    )
    # 0*0.30 + 0*0.25 + 0.5*0.20 + 0.5*0.25 = 0.225
    assert none == 0.225


def test_geo_score_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError):
        GeoScoreWeights(brand_mentioned=0.5, mention_position=0.5, sentiment=0.5, factual_accuracy=0.5)


def test_judge_response_heuristic_only() -> None:
    text = "Try thenautikal.com for cruise essentials kits."
    result = judge_response(response_text=text, prompt_text="What to pack?", skip_llm=True)
    assert result.brand_mentioned is True
    assert result.sentiment == 0.5
    assert result.factual_accuracy == 0.5
    assert result.judge_model == "heuristic-only"
    assert 0.0 <= result.geo_score <= 1.0
    row = result.to_score_row(raw_run_id="run-1")
    assert row["raw_run_id"] == "run-1"
    assert row["brand_mentioned"] is True


def test_judge_response_with_mocked_llm() -> None:
    completer = MagicMock()
    completer.complete.return_value = SimpleNamespace(
        text='{"sentiment": 0.9, "factual_accuracy": 0.8, "recommendation_rank": 1, "notes": "strong"}',
        tokens_in=100,
        tokens_out=40,
        cost_usd=0.001,
    )
    completer._model = "gpt-5-mini"

    result = judge_response(
        response_text="The Nautikal Essential 7 is a great cruise kit.",
        prompt_text="Best cruise accessories?",
        completer=completer,
        skip_llm=False,
    )
    assert result.brand_mentioned is True
    assert result.sentiment == 0.9
    assert result.factual_accuracy == 0.8
    assert result.judge_model == "gpt-5-mini"
    assert result.details["recommendation_rank"] == 1
    completer.complete.assert_called_once()


def test_default_weights_sum() -> None:
    w = DEFAULT_WEIGHTS
    assert abs(w.brand_mentioned + w.mention_position + w.sentiment + w.factual_accuracy - 1.0) < 1e-9


def test_fetch_unscored_raw_runs_filters_scored() -> None:
    mock_client = MagicMock()
    runs_chain = mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit
    runs_chain.return_value.execute.return_value.data = [
        {"id": "a", "status": "success", "response_text": "x"},
        {"id": "b", "status": "success", "response_text": "y"},
    ]
    # Second table("scores") call
    scores_table = MagicMock()
    scores_table.select.return_value.in_.return_value.execute.return_value.data = [{"raw_run_id": "a"}]

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
