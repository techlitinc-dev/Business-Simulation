"""Unit tests for GhostAgent personality rules (T43)."""

import pytest
from app.agents.ghost import GhostAgent
from app.agents.llm.base import MockProvider

OPTIONS = [
    {
        "option_id": "A",
        "name": "Bold attack",
        "description": "Spend big to win",
        "cash_impact_monthly": -15000,
        "probability_success": 0.9,
        "second_order_risk": "Cash burn",
        "required_execution": "Launch now",
    },
    {
        "option_id": "B",
        "name": "Hunker down",
        "description": "Cut spend",
        "cash_impact_monthly": -2000,
        "probability_success": 0.4,
        "second_order_risk": "Lose share",
        "required_execution": "Trim costs",
    },
    {
        "option_id": "C",
        "name": "Middle path",
        "description": "Moderate push",
        "cash_impact_monthly": -6000,
        "probability_success": 0.6,
        "second_order_risk": "Mixed",
        "required_execution": "Partial launch",
    },
]

HURDLE = {"event_id": "evt_1", "strategic_options": OPTIONS}


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider()


async def test_aggressive_picks_highest_success(provider: MockProvider) -> None:
    agent = GhostAgent(provider, "aggressive")
    decision = await agent.choose_option(HURDLE, {})
    assert decision.option_id == "A"
    assert decision.rationale


async def test_conservative_picks_lowest_cash_impact(provider: MockProvider) -> None:
    agent = GhostAgent(provider, "conservative")
    decision = await agent.choose_option(HURDLE, {})
    assert decision.option_id == "B"
    assert decision.rationale


async def test_opportunist_maximizes_expected_value(provider: MockProvider) -> None:
    agent = GhostAgent(provider, "opportunist")
    decision = await agent.choose_option(HURDLE, {})
    # Expected values: A: 0.9*-15000=-13500, B: 0.4*-2000=-800, C: 0.6*-6000=-3600
    assert decision.option_id == "B"
    assert decision.rationale


async def test_tie_break_aggressive_by_cash(provider: MockProvider) -> None:
    options = [
        {
            "option_id": "A",
            "name": "A",
            "description": "D",
            "cash_impact_monthly": -10000,
            "probability_success": 0.7,
            "second_order_risk": "R",
            "required_execution": "E",
        },
        {
            "option_id": "B",
            "name": "B",
            "description": "D",
            "cash_impact_monthly": -20000,
            "probability_success": 0.7,
            "second_order_risk": "R",
            "required_execution": "E",
        },
    ]
    agent = GhostAgent(provider, "aggressive")
    decision = await agent.choose_option(
        {"event_id": "e", "strategic_options": options}, {}
    )
    # Same success probability → highest cash impact (least negative) wins.
    assert decision.option_id == "A"


async def test_llm_option_id_validated_against_hurdle(provider: MockProvider) -> None:
    """A mock/LLM pick not in the options falls back to the rule."""
    provider.register(
        "Choose the best strategic option",
        '{"option_id": "ZZZ", "rationale": "bad"}',
    )
    agent = GhostAgent(provider, "conservative")
    decision = await agent.choose_option(HURDLE, {})
    # Falls back to the conservative rule.
    assert decision.option_id == "B"
