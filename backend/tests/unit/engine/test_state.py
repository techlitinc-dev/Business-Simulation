"""Tests for the engine state model and blueprint -> state compiler."""

import json
from pathlib import Path

import pytest
from app.engine.state import (
    MarketState,
    RevenueStream,
    Trigger,
    compile_blueprint,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _golden() -> dict:
    return json.loads((FIXTURES / "blueprint_golden.json").read_text())


def test_compile_golden_blueprint() -> None:
    state = compile_blueprint(_golden())
    assert state.month == 0
    assert state.financials.cash == 380000.0
    assert state.financials.monthly_burn == 60000.0
    assert len(state.streams) == 1
    stream = state.streams[0]
    assert stream.name == "Core SaaS"
    assert stream.customers == 0
    assert state.triggers_fired == []
    assert state.bankrupt is False


def test_team_members_compiled() -> None:
    state = compile_blueprint(_golden())
    team = state.financials.team
    assert len(team) == 2
    assert team[0].role == "CEO/Founder"
    assert team[0].salary_annual == 80000.0
    assert team[0].hire_month == 0
    assert team[1].hire_month == 3


def test_missing_starting_capital_raises() -> None:
    payload = _golden()
    del payload["financials"]["starting_capital"]
    with pytest.raises(ValueError, match="starting_capital"):
        compile_blueprint(payload)


def test_empty_streams_raises() -> None:
    payload = _golden()
    payload["revenue_engine"]["streams"] = []
    with pytest.raises(ValueError, match="streams"):
        compile_blueprint(payload)


def test_missing_streams_key_raises() -> None:
    payload = _golden()
    del payload["revenue_engine"]["streams"]
    with pytest.raises(ValueError, match="streams"):
        compile_blueprint(payload)


def test_missing_cost_structure_raises() -> None:
    payload = _golden()
    del payload["cost_structure"]
    with pytest.raises(ValueError, match="cost_structure"):
        compile_blueprint(payload)


def test_snapshot_is_deep_copy() -> None:
    state = compile_blueprint(_golden())
    snap = state.snapshot()
    snap.financials.cash = 1.0
    assert state.financials.cash == 380000.0
    assert snap is not state


def test_engine_has_no_forbidden_imports() -> None:
    forbidden = ("fastapi", "sqlalchemy", "pydantic", "app.core", "app.db", "app.models")
    engine_dir = Path(__file__).resolve().parents[3] / "app" / "engine"
    for path in engine_dir.rglob("*.py"):
        source = path.read_text()
        for line in source.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lower = stripped.lower()
            for token in forbidden:
                assert token not in lower, f"{path}: forbidden import token '{token}': {stripped}"


def test_seasonality_wrong_length_raises() -> None:
    payload = _golden()
    payload["simulation_parameters"]["seasonality"] = [1.0, 2.0]
    with pytest.raises(ValueError, match="12 entries"):
        compile_blueprint(payload)


def test_defaults_applied() -> None:
    state = compile_blueprint(_golden())
    fin = state.financials
    market = state.market
    assert fin.gross_margin == 0.8
    assert fin.ar_days == 30
    assert fin.ap_days == 30
    assert market.price == 99.0
    assert market.reference_price == 99.0
    assert market.base_demand == pytest.approx(1500 / 12)
    assert market.market_size == 150000
    assert market.market_share == 0.0
    assert market.price_elasticity == -1.5
    assert market.competitor_pressure == 0.0
    assert market.brand_sentiment == 0.5
    assert market.seasonality == [1.0] * 12
    assert state.streams[0].customers == 0


def test_optional_overrides_respected() -> None:
    payload = _golden()
    payload["financials"]["gross_margin"] = 0.7
    payload["financials"]["ar_days"] = 0
    payload["financials"]["ap_days"] = 15
    payload["simulation_parameters"]["price_elasticity"] = -2.0
    payload["simulation_parameters"]["seasonality"] = [1.2] * 12
    state = compile_blueprint(payload)
    assert state.financials.gross_margin == 0.7
    assert state.financials.ar_days == 0
    assert state.financials.ap_days == 15
    assert state.market.price_elasticity == -2.0
    assert state.market.seasonality == [1.2] * 12


def test_market_state_sentiment_default() -> None:
    market = MarketState(
        market_size=1000,
        market_share=0.0,
        base_demand=50.0,
        price=10.0,
        reference_price=10.0,
        price_elasticity=-1.5,
        seasonality=[1.0] * 12,
        competitor_pressure=0.0,
    )
    assert market.brand_sentiment == 0.5


def test_trigger_enum_members() -> None:
    assert list(Trigger) == [
        Trigger.BANKRUPTCY,
        Trigger.PROFITABILITY,
        Trigger.FUNDING_NEED,
        Trigger.MILESTONE,
    ]


def test_revenue_stream_default_customers() -> None:
    stream = RevenueStream("s", "Subscription", 10.0, 100, 500.0, 100.0, 0.05)
    assert stream.customers == 0
