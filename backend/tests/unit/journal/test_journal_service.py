"""Unit tests for the decision journal scoring (Day journal)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from app.services.journal.journal_service import (
    _is_positive_outcome,
    _is_positive_projection,
    score_decision,
)


def _run(result: dict[str, Any] | None) -> MagicMock:
    run = MagicMock()
    run.result = result
    return run


def _decision(projection: dict[str, Any] | None, option_id: str = "opt_a") -> MagicMock:
    decision = MagicMock()
    decision.option_id = option_id
    decision.projection = projection
    return decision


def test_score_positive_projection_and_survival() -> None:
    """Followed the AI path (positive projection) and the run survived → 1.0."""
    decision = _decision({"survives": True, "end_cash": 50000})
    run = _run({"survived": True, "final_cash": 42000})
    assert score_decision(decision, run) == 1.0


def test_score_survived_despite_negative_projection() -> None:
    """Run survived but the chosen option's projection was negative → 0.5."""
    decision = _decision({"survives": False, "end_cash": -5000})
    run = _run({"survived": True, "final_cash": 1000})
    assert score_decision(decision, run) == 0.5


def test_score_negative_outcome() -> None:
    """Run died → 0.0 regardless of projection."""
    decision = _decision({"survives": True, "end_cash": 50000})
    run = _run({"survived": False, "final_cash": -20000})
    assert score_decision(decision, run) == 0.0


def test_score_missing_data_defaults_to_zero() -> None:
    """No projection and no result → 0.0."""
    decision = _decision(None)
    run = _run(None)
    assert score_decision(decision, run) == 0.0


def test_is_positive_outcome_uses_survived_flag() -> None:
    assert _is_positive_outcome({"survived": True}) is True
    assert _is_positive_outcome({"survived": False}) is False
    assert _is_positive_outcome(None) is False


def test_is_positive_projection_uses_survives_flag() -> None:
    assert _is_positive_projection({"survives": True}) is True
    assert _is_positive_projection({"survives": False}) is False
    assert _is_positive_projection(None) is False
