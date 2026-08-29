"""Day 32 — gamification, cost guard, i18n, and model routing tests."""

from __future__ import annotations

import pytest
from app.services.gamification.achievements import check_achievements


def _ids(earned: list[object]) -> list[str]:
    return [a.id for a in earned]  # type: ignore[attr-defined]


def test_first_run_achievement_earned() -> None:
    earned = check_achievements({"total_runs": 1})
    assert "first_run" in _ids(earned)


def test_top_decile_requires_90th_percentile() -> None:
    assert "top_decile" not in _ids(check_achievements({"cohort_percentile": 89}))
    assert "top_decile" in _ids(check_achievements({"cohort_percentile": 90}))


def test_ai_challenger_requires_5_beats() -> None:
    assert "beat_ai_5" not in _ids(
        check_achievements({"beat_ai_count": 4, "total_runs": 1})
    )
    assert "beat_ai_5" in _ids(
        check_achievements({"beat_ai_count": 5, "total_runs": 1})
    )


async def test_cost_guard_monthly_budget() -> None:
    """Usage above the monthly token limit raises HTTP 429."""
    from unittest.mock import patch

    from app.services.cost_guard import MONTHLY_TOKEN_LIMIT, check_monthly_budget

    with patch("app.services.cost_guard._get_redis") as mock_redis:
        r = mock_redis.return_value
        r.get.return_value = str(MONTHLY_TOKEN_LIMIT + 1)
        with pytest.raises(Exception) as exc_info:
            await check_monthly_budget("ws_001")
        assert exc_info.value.status_code == 429


def test_i18n_language_instruction_en_is_empty() -> None:
    from app.utils.i18n import get_language_instruction

    assert get_language_instruction("en") == ""


def test_i18n_language_instruction_es_contains_spanish() -> None:
    from app.utils.i18n import get_language_instruction

    instruction = get_language_instruction("es")
    assert "Spanish" in instruction


def test_model_router_falls_back_to_default() -> None:
    from app.agents.llm.router import get_model_for_task

    model = get_model_for_task("unknown_task")
    assert model == "deepseek-chat"  # falls back to LLM_MODEL


def test_format_currency_usd() -> None:
    from app.utils.i18n import format_currency

    assert format_currency(1500, "USD") == "$1,500"
