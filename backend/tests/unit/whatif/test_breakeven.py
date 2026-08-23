"""Unit tests for the what-if breakeven service (Day 08)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.whatif.breakeven import find_breakeven
from app.services.whatif.schemas import BreakevenRequest


def _req(**overrides: Any) -> BreakevenRequest:
    base: dict[str, Any] = {
        "workspace_id": uuid.uuid4(),
        "blueprint_id": "bp_001",
        "param": "revenue_engine.streams.0.churn_monthly",
        "search_min": 0.02,
        "search_max": 0.12,
        "target_survival": 0.5,
    }
    base.update(overrides)
    return BreakevenRequest(**base)


async def _run_breakeven() -> Any:
    """Run find_breakeven with the engine mocked so survival crosses at churn 0.07."""
    payload_mock = MagicMock()
    payload_mock.model_dump.return_value = {
        "revenue_engine": {"streams": [{"churn_monthly": 0.05}]}
    }

    with (
        patch(
            "app.services.whatif.breakeven.get_version_payload",
            new_callable=AsyncMock,
        ) as mock_bp,
        patch("app.services.whatif.breakeven._simulate_lifespans") as mock_lifespans,
    ):
        mock_bp.return_value = payload_mock

        def lifespans_for(
            payload: dict[str, Any], n_runs: int, base_seed: int = 0
        ) -> list[float]:
            churn = payload["revenue_engine"]["streams"][0]["churn_monthly"]
            month = 24.0 if churn < 0.07 else 14.0
            return [month] * n_runs

        mock_lifespans.side_effect = lifespans_for
        return await find_breakeven(_req(), AsyncMock())


async def test_breakeven_returns_result() -> None:
    result = await _run_breakeven()
    assert 0.02 <= result.breakeven_value <= 0.12


async def test_breakeven_message_contains_param_name() -> None:
    result = await _run_breakeven()
    assert "revenue_engine.streams.0.churn_monthly" in result.message


async def test_breakeven_survival_in_range() -> None:
    result = await _run_breakeven()
    assert 0.0 <= result.survival_at_breakeven <= 1.0
