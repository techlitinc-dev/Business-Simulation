"""Unit tests for gamification, cost guard, i18n, and model routing."""

from __future__ import annotations

import fakeredis.aioredis
import pytest
from app.core.exceptions import DomainError
from app.services.cost_guard import (
    REPORT_TOKEN_LIMIT,
    CostLimitExceeded,
    check_report_budget,
    record_report_usage,
)
from app.services.gamification.achievements import ACHIEVEMENTS, check_achievements


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


def test_shock_absorber_requires_3_shocks() -> None:
    assert "survived_3_shocks" not in _ids(check_achievements({"demand_shocks_survived": 2}))
    assert "survived_3_shocks" in _ids(check_achievements({"demand_shocks_survived": 3}))


def test_achievements_all_have_unique_ids() -> None:
    ids = [a.id for a in ACHIEVEMENTS]
    assert len(ids) == len(set(ids))


async def test_report_budget_enforced_via_fakeredis() -> None:
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await record_report_usage("job_1", REPORT_TOKEN_LIMIT, r=r)
    with pytest.raises(CostLimitExceeded) as exc_info:
        await check_report_budget("job_1", amount=1, r=r)
    assert exc_info.value.status_code == 429
    assert exc_info.value.scope == "report"


async def test_report_budget_below_limit_passes() -> None:
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await record_report_usage("job_2", 100, r=r)
    await check_report_budget("job_2", amount=1, r=r)  # no raise


async def test_report_budget_unknown_job_passes() -> None:
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await check_report_budget("job_missing", r=r)  # no raise


def test_cost_limit_exceeded_is_domain_error() -> None:
    exc = CostLimitExceeded(used=10, limit=100, scope="report")
    assert isinstance(exc, DomainError)
    assert exc.status_code == 429


def test_i18n_language_instruction_en_is_empty() -> None:
    from app.utils.i18n import get_language_instruction

    assert get_language_instruction("en") == ""


def test_i18n_language_instruction_es_contains_spanish() -> None:
    from app.utils.i18n import get_language_instruction

    instruction = get_language_instruction("es")
    assert "Spanish" in instruction


def test_i18n_unsupported_language_falls_back_to_english() -> None:
    from app.utils.i18n import get_language_instruction

    instruction = get_language_instruction("xx")
    assert "English" in instruction


def test_i18n_currency_formatting() -> None:
    from app.utils.i18n import format_currency

    assert format_currency(1234.6, "USD") == "$1,235"
    assert format_currency(1234.6, "EUR") == "€1,235"
    assert format_currency(1234.6, "BRL") == "R$1,235"
    assert format_currency(1234.6, "ZZZ") == "$1,235"  # default USD


def test_model_router_defaults_to_llm_model() -> None:
    from app.agents.llm.router import get_model_for_task

    model = get_model_for_task("executive_summary")
    assert model  # falls back to the configured llm_model


def test_model_router_uses_override() -> None:
    from app.agents.llm.router import TASK_MODEL_FIELD_MAP, get_model_for_task
    from app.core.config import get_settings

    settings = get_settings()
    field = TASK_MODEL_FIELD_MAP["counterfactual"]
    previous = getattr(settings, field)
    try:
        setattr(settings, field, "deepseek-reasoner")
        assert get_model_for_task("counterfactual") == "deepseek-reasoner"
        # Unmapped tasks fall back to the default model field.
        assert get_model_for_task("unknown_task") == settings.llm_model
    finally:
        setattr(settings, field, previous)
