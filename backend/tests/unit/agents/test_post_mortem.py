"""Unit tests for the post-mortem agent (T31)."""

import json

from app.agents.llm.base import MockProvider
from app.agents.post_mortem import PostMortemAgent, _fallback_output
from app.schemas.report import (
    KillVector,
    PostMortemOutput,
    SurvivalMetrics,
    TweakResult,
)


def _metrics() -> SurvivalMetrics:
    return SurvivalMetrics(
        survival_rate=0.34,
        runs_total=100,
        runs_survived=34,
        median_lifespan_months=11,
        kill_vectors=[
            KillVector(cause="financial", count=30, pct=45.5),
            KillVector(cause="market", count=22, pct=33.3),
        ],
    )


def _deltas() -> list[TweakResult]:
    return [
        TweakResult(
            tweak_key="churn", label="Reduce churn by 20%", delta_pp=12.0,
            baseline_survival=0.34, tweaked_survival=0.46,
        ),
        TweakResult(
            tweak_key="cac", label="Reduce CAC by 20%", delta_pp=5.0,
            baseline_survival=0.34, tweaked_survival=0.39,
        ),
        TweakResult(
            tweak_key="price", label="Raise price by 10%", delta_pp=-3.0,
            baseline_survival=0.34, tweaked_survival=0.31,
        ),
    ]


def _blueprint() -> dict:
    return {"name": "test"}


def _canned_post_mortem() -> str:
    return json.dumps(
        {
            "optimizations": [
                {
                    "recommendation": "Cut churn with onboarding emails.",
                    "implementation_cost": "Low",
                    "trade_off": "Slight near-term spend.",
                    "tweak_key": "churn",
                }
            ],
            "counter_factual_insight": "Churn is the top lever.",
            "blueprint_v2_suggestions": ["Focus on retention."],
        }
    )


async def test_generate_returns_valid_output() -> None:
    provider = MockProvider()
    provider.register("post-mortem", _canned_post_mortem())
    agent = PostMortemAgent(provider)
    output = await agent.generate(_metrics(), _deltas(), _blueprint())
    assert isinstance(output, PostMortemOutput)
    assert output.optimizations[0]["tweak_key"] == "churn"
    assert output.counter_factual_insight


async def test_mock_fallback_without_key() -> None:
    provider = MockProvider()  # no registered substrings
    agent = PostMortemAgent(provider)
    output = await agent.generate(_metrics(), _deltas(), _blueprint())
    assert isinstance(output, PostMortemOutput)
    assert len(output.optimizations) >= 1
    assert output.counter_factual_insight


async def test_invalid_llm_falls_back_to_engine_deltas() -> None:
    provider = MockProvider()
    provider.register("post-mortem", "not json at all")
    agent = PostMortemAgent(provider)
    output = await agent.generate(_metrics(), _deltas(), _blueprint())
    assert isinstance(output, PostMortemOutput)
    assert len(output.optimizations) >= 1


def test_fallback_output_ranks_by_delta() -> None:
    output = _fallback_output(_deltas())
    assert output.optimizations[0]["tweak_key"] == "churn"  # highest delta
    assert "12.0" in output.optimizations[0]["recommendation"]
