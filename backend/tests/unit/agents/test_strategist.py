"""Strategist tests (T24): schema bounds, determinism, survival logic, advise."""

import json
from pathlib import Path

from app.agents.chronicle import Chronicle
from app.agents.llm.base import MockProvider
from app.agents.strategist import Strategist
from app.engine.loop import run_simulation
from app.engine.state import compile_blueprint
from app.schemas.decision import StrategicOption
from app.schemas.hurdle import HurdleEvent

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _state_at_month(month: int):
    payload = json.loads((FIXTURES / "blueprint_golden.json").read_text())
    result = run_simulation(compile_blueprint(payload), month, seed=42)
    kpis = result.tick_logs[-1].kpis if result.tick_logs else {}
    return result.final_state, kpis


def _hurdle() -> HurdleEvent:
    return HurdleEvent.model_validate(
        {
            "event_id": "evt_001",
            "trigger_timing": "month 7",
            "category": "market",
            "narrative": {
                "title": "Competitor launches freemium",
                "story": "A rival undercuts pricing.",
                "source_actor": "Competitor X",
                "believability_score": 0.85,
            },
            "mechanical_impact": {
                "immediate": {"cac_delta_percent": 35, "churn_delta_percent": 15},
                "cascading": {},
            },
            "ai_game_master_note": "Concentration.",
        }
    )


def _canned_options(n: int) -> str:
    options = []
    for i in range(n):
        options.append(
            {
                "option_id": "ABCD"[i],
                "name": f"Option {i+1}",
                "description": f"Strategy {i+1}.",
                "cash_impact_monthly": -1000 * i,
                "probability_success": 0.6,
                "second_order_risk": "Risk of option.",
                "required_execution": "Execute steps.",
            }
        )
    return json.dumps({"options": options})


async def test_propose_returns_exactly_3_options() -> None:
    state, kpis = _state_at_month(7)
    provider = MockProvider()
    provider.register("Advise on this hurdle", _canned_options(3))
    strategist = Strategist(provider)
    options = await strategist.propose_options(state, kpis, _hurdle(), Chronicle())
    assert len(options) == 3
    assert all(o.option_id and o.second_order_risk and o.required_execution for o in options)


async def test_one_or_five_options_fails_and_repairs() -> None:
    state, kpis = _state_at_month(7)
    provider = MockProvider()
    # First response has 1 option (below min_length=2) -> repair returns 3.
    provider.register("failed validation", _canned_options(3))
    provider.register("Advise on this hurdle", _canned_options(1))
    strategist = Strategist(provider)
    options = await strategist.propose_options(state, kpis, _hurdle(), Chronicle())
    assert len(options) == 3


def test_projection_deterministic_and_12_months() -> None:
    state, kpis = _state_at_month(7)
    option = StrategicOption(
        option_id="A", name="Cut", description="Cut burn.",
        cash_impact_monthly=-5000, probability_success=0.6,
        second_order_risk="Growth stalls", required_execution="Layoffs",
    )
    strategist = Strategist(MockProvider())
    a = strategist.project_option(state, option, _hurdle(), seed=1)
    b = strategist.project_option(state, option, _hurdle(), seed=1)
    assert len(a.monthly_cash) == 12
    assert a == b
    assert a.survives == (a.min_cash >= 0)


def test_projection_reports_death_when_impact_too_large() -> None:
    state, kpis = _state_at_month(7)
    option = StrategicOption(
        option_id="B", name="Mega spend", description="Huge bet.",
        cash_impact_monthly=-10_000_000, probability_success=0.1,
        second_order_risk="Bankruptcy", required_execution="Raise capital",
    )
    strategist = Strategist(MockProvider())
    projection = strategist.project_option(state, option, _hurdle(), seed=0)
    assert projection.survives is False
    assert projection.min_cash < 0


def test_projection_no_llm_calls() -> None:
    """project_option is pure engine math — assert no provider completion happens."""
    state, kpis = _state_at_month(7)
    option = StrategicOption(
        option_id="C", name="Hold", description="Do nothing.",
        cash_impact_monthly=0, probability_success=0.4,
        second_order_risk="Status quo", required_execution="Wait",
    )
    calls = []

    class CountingProvider(MockProvider):
        async def complete(self, system, user, **kwargs):
            calls.append(1)
            return await super().complete(system, user, **kwargs)

    strategist = Strategist(CountingProvider())
    strategist.project_option(state, option, _hurdle(), seed=2)
    assert calls == []


async def test_advise_aligns_options_and_projections() -> None:
    state, kpis = _state_at_month(7)
    provider = MockProvider()
    provider.register("Advise on this hurdle", _canned_options(2))
    strategist = Strategist(provider)
    result = await strategist.advise(state, kpis, _hurdle(), Chronicle())
    assert len(result.options) == 2
    assert len(result.projections) == 2
    option_ids = [o.option_id for o in result.options]
    projection_ids = [p.option_id for p in result.projections]
    assert option_ids == projection_ids
    assert result.hurdle_id == "evt_001"
