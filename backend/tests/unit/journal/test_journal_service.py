"""Unit tests for the decision journal scoring + playbook generation (Day 28 spec)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.playbook_writer import Playbook, generate_playbook
from app.services.journal.journal_service import score_decision


def _run(result: dict[str, Any] | None) -> MagicMock:
    run = MagicMock()
    run.result = result
    return run


def _decision(projection: dict[str, Any] | None, option_id: str = "opt_a") -> MagicMock:
    decision = MagicMock()
    decision.option_id = option_id
    decision.projection = projection
    return decision


async def test_score_positive_following_ai() -> None:
    """Positive projection and the run survived (followed AI) -> 1.0."""
    decision = _decision({"survives": True, "end_cash": 50000})
    run = _run({"survived": True, "final_cash": 42000})
    assert score_decision(decision, run) == 1.0


async def test_score_positive_not_following_ai() -> None:
    """Run survived but the chosen option's projection was negative -> 0.5."""
    decision = _decision({"survives": False, "end_cash": -5000})
    run = _run({"survived": True, "final_cash": 1000})
    assert score_decision(decision, run) == 0.5


async def test_score_negative_outcome() -> None:
    """Run died -> 0.0 regardless of projection."""
    decision = _decision({"survives": True, "end_cash": 50000})
    run = _run({"survived": False, "final_cash": -20000})
    assert score_decision(decision, run) == 0.0


async def test_generate_playbook_returns_playbook() -> None:
    """MockProvider -> validated Playbook with title and >=3 steps."""
    from app.agents.llm.base import MockProvider

    canned = (
        '{"title": "Surviving a Demand Shock", "scenario_type": "market", '
        '"situation": "Use when demand collapses.", '
        '"steps": ["Cut burn", "Re-negotiate vendors", "Watch cash"], '
        '"key_metrics_to_watch": ["cash_balance", "runway_months"], '
        '"expected_outcome": "Stabilized runway.", '
        '"source_run_summary": "Mock run"}'
    )
    provider = MockProvider()
    provider.register("Generate a reusable playbook", canned)

    with patch(
        "app.agents.playbook_writer._make_provider", return_value=provider
    ):
        playbook = await generate_playbook({}, {"summary": "Mock run"})

    assert isinstance(playbook, Playbook)
    assert playbook.title == "Surviving a Demand Shock"
    assert len(playbook.steps) >= 3
    assert playbook.key_metrics_to_watch


async def test_journal_summary_beat_ai_pct() -> None:
    """3 decisions, 2 beat AI -> beat_ai_pct == 66.7."""
    from app.services.journal.journal_service import get_workspace_journal_summary

    entries = [
        MagicMock(beat_ai=True),
        MagicMock(beat_ai=True),
        MagicMock(beat_ai=False),
    ]
    db = AsyncMock()
    run_ids = MagicMock()
    run_ids.all.return_value = ["run_1"]
    db.scalars = AsyncMock(return_value=run_ids)

    with patch(
        "app.services.journal.journal_service.get_run_journal",
        new_callable=AsyncMock,
        return_value=entries,
    ):
        summary = await get_workspace_journal_summary("ws_1", db)

    assert summary.total_decisions == 3
    assert summary.beat_ai_count == 2
    assert summary.beat_ai_pct == 66.7
    assert "2 of 3" in summary.summary
