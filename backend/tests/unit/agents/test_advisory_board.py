"""Unit tests for the advisory board agent (Day 16)."""

from __future__ import annotations

import json

from app.agents.advisory_board import run_advisory_board
from app.core.config import get_settings

MOCK_BLUEPRINT = {
    "monthly_churn": 0.05, "price": 99, "cac": 450,
    "starting_capital": 100000, "fixed_monthly_costs": 15000,
}
MOCK_RUN_SUMMARY = {
    "survival_rate": 0.58, "resilience_score": 54.0,
    "median_lifespan": 14,
}


def _force_mock() -> None:
    settings = get_settings()
    settings.llm_provider = "mock"
    settings.llm_api_key = ""


async def test_advisory_board_returns_four_reviews() -> None:
    _force_mock()
    result = await run_advisory_board(MOCK_BLUEPRINT, MOCK_RUN_SUMMARY)
    assert len(result["reviews"]) == 4


async def test_advisory_board_persona_names_correct() -> None:
    _force_mock()
    result = await run_advisory_board(MOCK_BLUEPRINT, MOCK_RUN_SUMMARY)
    personas = {r["persona"] for r in result["reviews"]}
    assert personas == {"CFO", "CMO", "RiskAuditor", "Operator"}


async def test_advisory_board_summary_has_required_fields() -> None:
    _force_mock()
    result = await run_advisory_board(MOCK_BLUEPRINT, MOCK_RUN_SUMMARY)
    summary = result["summary"]
    assert "consensus_verdict" in summary
    assert "points_of_agreement" in summary
    assert len(summary["points_of_agreement"]) >= 1
    assert summary["overall_risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


async def test_advisory_board_result_serializable() -> None:
    _force_mock()
    result = await run_advisory_board(MOCK_BLUEPRINT, MOCK_RUN_SUMMARY)
    json.dumps(result)  # must not raise


async def test_each_review_has_top_concerns() -> None:
    _force_mock()
    result = await run_advisory_board(MOCK_BLUEPRINT, MOCK_RUN_SUMMARY)
    for review in result["reviews"]:
        assert review["persona"]
        assert isinstance(review["top_concerns"], list)
        assert len(review["top_concerns"]) >= 1


async def test_summary_agreement_list_non_empty() -> None:
    _force_mock()
    result = await run_advisory_board(MOCK_BLUEPRINT, MOCK_RUN_SUMMARY)
    assert len(result["summary"]["points_of_agreement"]) >= 1
