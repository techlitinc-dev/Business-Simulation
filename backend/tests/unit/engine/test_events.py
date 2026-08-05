"""Tests for the deterministic event injector (T15)."""

import pytest
from app.engine.events import (
    ActiveEffect,
    apply_due_events,
    apply_event,
    validate_mechanical_impact,
)
from app.engine.state import BusinessState, FinancialState, MarketState, RevenueStream


def _state() -> BusinessState:
    fin = FinancialState(
        cash=500000.0,
        mrr=0.0,
        arr=0.0,
        monthly_burn=45000.0,
        fixed_monthly=35000.0,
        variable_per_unit=12.0,
        ar_days=30,
        ap_days=30,
        gross_margin=0.8,
        team=[],
    )
    market = MarketState(
        market_size=50000,
        market_share=0.0,
        base_demand=100.0,
        price=99.0,
        reference_price=99.0,
        price_elasticity=-1.5,
        seasonality=[1.0] * 12,
        competitor_pressure=0.0,
        brand_sentiment=0.5,
    )
    stream = RevenueStream(
        "Core SaaS", "Subscription", 99.0, 500, 2400.0, 850.0, 0.05, customers=100
    )
    return BusinessState(month=6, financials=fin, market=market, streams=[stream])


def test_validate_drops_unknown_and_defaults_missing() -> None:
    with pytest.warns(UserWarning, match="unknown"):
        result = validate_mechanical_impact(
            {"immediate": {"bogus_key": 99, "cac_delta_percent": 10}}
        )
    assert "bogus_key" not in result
    assert result["cac_delta_percent"] == 10.0
    assert result["churn_delta_percent"] == 0.0
    assert result["new_signups_delta_percent"] == 0.0


def test_validate_clamps_extremes() -> None:
    result = validate_mechanical_impact(
        {"immediate": {"cac_delta_percent": 500, "new_signups_delta_percent": -100}}
    )
    assert result["cac_delta_percent"] == 200.0
    assert result["new_signups_delta_percent"] == -90.0


def test_validate_accepts_wrapped_and_flat() -> None:
    wrapped = validate_mechanical_impact({"immediate": {"cac_delta_percent": 5}})
    assert wrapped["cac_delta_percent"] == 5.0
    flat = validate_mechanical_impact({"cac_delta_percent": 5})
    assert flat["cac_delta_percent"] == 5.0


def test_apply_event_evt001_effects() -> None:
    state = _state()
    impact = {
        "immediate": {
            "cac_delta_percent": 35,
            "churn_delta_percent": 15,
            "new_signups_delta_percent": -40,
            "team_morale_delta": -0.10,
            "cash_burn_delta_monthly": 0,
        }
    }
    result = apply_event(state, impact, month=7)
    stream = result.streams[0]
    assert stream.churn_monthly == pytest.approx(0.05 * 1.15)
    assert stream.cac == pytest.approx(850.0 * 1.35)
    assert len(result.active_event_effects) == 1
    effect = result.active_event_effects[0]
    assert effect["remaining_months"] == 3
    assert effect["deltas"]["new_signups_delta_percent"] == -40.0
    assert effect["deltas"]["churn_delta_percent"] == 15.0
    # input not mutated
    assert state.streams[0].churn_monthly == 0.05
    assert state.streams[0].cac == 850.0
    assert state.active_event_effects == []


def test_apply_event_one_time_cash_and_burn() -> None:
    state = _state()
    result = apply_event(
        state,
        {"immediate": {"cash_delta_one_time": -5000, "cash_burn_delta_monthly": 2000}},
        month=7,
    )
    assert result.financials.cash == pytest.approx(500000.0 - 5000.0)
    assert result.financials.fixed_monthly == pytest.approx(37000.0)
    assert result.financials.monthly_burn == pytest.approx(47000.0)


def test_apply_event_churn_clamps() -> None:
    state = _state()
    state.streams[0].churn_monthly = 0.94
    result = apply_event(state, {"immediate": {"churn_delta_percent": 200}}, month=7)
    assert result.streams[0].churn_monthly == pytest.approx(0.95)
    state2 = _state()
    state2.streams[0].churn_monthly = 0.002
    result2 = apply_event(state2, {"immediate": {"churn_delta_percent": -90}}, month=7)
    assert result2.streams[0].churn_monthly == pytest.approx(0.001)


def test_apply_event_market_shock() -> None:
    state = _state()
    result = apply_event(
        state,
        {"immediate": {"competitor_pressure_delta": 0.3, "sentiment_delta": -0.1}},
        month=7,
    )
    assert result.market.competitor_pressure == pytest.approx(0.3)
    assert result.market.brand_sentiment == pytest.approx(0.4)
    assert state.market.competitor_pressure == 0.0


def test_apply_due_events_decays_and_removes() -> None:
    state = _state()
    state.active_event_effects = [
        ActiveEffect(remaining_months=3, deltas={"new_signups_delta_percent": -40.0}).__dict__
    ]
    s2 = apply_due_events(state, month=7)
    assert s2.active_event_effects[0]["remaining_months"] == 2
    s3 = apply_due_events(s2, month=8)
    assert s3.active_event_effects[0]["remaining_months"] == 1
    s4 = apply_due_events(s3, month=9)
    assert s4.active_event_effects == []


def test_no_active_effect_without_persistent_deltas() -> None:
    state = _state()
    result = apply_event(state, {"immediate": {"cash_delta_one_time": -100}}, month=7)
    assert result.active_event_effects == []
