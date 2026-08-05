"""Tests for the monthly time-step loop and trigger checks."""

import json
import random
from pathlib import Path

from app.engine.loop import check_triggers, run_simulation, tick
from app.engine.state import (
    BusinessState,
    FinancialState,
    MarketState,
    RevenueStream,
    Trigger,
    compile_blueprint,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _golden() -> dict:
    return json.loads((FIXTURES / "blueprint_golden.json").read_text())


def _compile(golden: dict) -> BusinessState:
    return compile_blueprint(golden)


def test_baseline_survives_24_months() -> None:
    state = _compile(_golden())
    result = run_simulation(state, 24, seed=42)
    assert result.months_simulated == 24
    assert len(result.tick_logs) == 24
    assert result.survived is True


def test_bankruptcy_early_exit() -> None:
    payload = _golden()
    payload["financials"]["starting_capital"] = 50000
    result = run_simulation(_compile(payload), 24, seed=42)
    assert result.final_state.bankrupt is True
    assert any(ev.trigger == Trigger.BANKRUPTCY for ev in result.triggers)
    assert result.months_simulated < 24
    assert result.survived is False


def test_determinism_same_seed() -> None:
    state = _compile(_golden())
    a = run_simulation(state, 24, seed=42)
    b = run_simulation(state, 24, seed=42)
    for ta, tb in zip(a.tick_logs, b.tick_logs, strict=True):
        assert ta.kpis == tb.kpis


def test_different_seed_reproducible() -> None:
    state = _compile(_golden())
    a = run_simulation(state, 24, seed=43)
    b = run_simulation(state, 24, seed=43)
    assert [t.kpis for t in a.tick_logs] == [t.kpis for t in b.tick_logs]
    baseline = run_simulation(state, 24, seed=42)
    seed43 = [t.kpis for t in a.tick_logs]
    seed42 = [t.kpis for t in baseline.tick_logs]
    assert seed43[0] != seed42[0] or seed43[11] != seed42[11]


def test_funding_need_fires_once() -> None:
    state = _compile(_golden())
    result = run_simulation(state, 24, seed=42)
    funding = [ev for ev in result.triggers if ev.trigger == Trigger.FUNDING_NEED]
    assert len(funding) == 1


def test_profitability_trigger_exact_month() -> None:
    payload = _golden()
    payload["financials"]["starting_capital"] = 1000000
    payload["cost_structure"]["burn_rate_month_1"] = 1000
    payload["cost_structure"]["fixed_monthly"] = 1000
    payload["cost_structure"]["variable_per_unit"] = 0
    payload["cost_structure"]["team"] = []
    payload["revenue_engine"]["streams"][0]["projected_customers_month_12"] = 5000
    payload["revenue_engine"]["streams"][0]["price_point"] = 99
    state = _compile(payload)
    result = run_simulation(state, 24, seed=42)
    profitability = [ev for ev in result.triggers if ev.trigger == Trigger.PROFITABILITY]
    assert len(profitability) == 1
    # Find the 3rd consecutive profitable month
    profitable_months = [log.month for log in result.tick_logs if log.kpis["burn"] < 0]
    assert len(profitable_months) >= 3
    assert profitability[0].month == profitable_months[2]


def test_global_random_not_used() -> None:
    state = _compile(_golden())
    random.seed(999)
    a = run_simulation(state, 24, seed=42)
    random.seed(777)
    b = run_simulation(state, 24, seed=42)
    assert [t.kpis for t in a.tick_logs] == [t.kpis for t in b.tick_logs]


def test_check_triggers_bankruptcy_sets_flag() -> None:
    fin = FinancialState(
        cash=-1.0, mrr=0.0, arr=0.0, monthly_burn=1000.0, fixed_monthly=1000.0,
        variable_per_unit=0.0, ar_days=30, ap_days=30, gross_margin=0.8, team=[],
    )
    market = MarketState(50000, 0.0, 41.67, 99.0, 99.0, -1.5, [1.0] * 12, 0.0)
    stream = RevenueStream("s", "Subscription", 99.0, 500, 2400.0, 850.0, 0.05)
    state = BusinessState(month=5, financials=fin, market=market, streams=[stream])
    fired = check_triggers(state)
    assert any(ev.trigger == Trigger.BANKRUPTCY for ev in fired)
    assert state.bankrupt is True


def test_tick_increments_month() -> None:
    state = _compile(_golden())
    next_state = tick(state, random.Random(42))
    assert next_state.month == 1
