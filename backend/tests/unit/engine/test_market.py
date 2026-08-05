"""Tests for market dynamics: demand, elasticity, seasonality, competitor pressure."""

import random

import pytest
from app.engine.market import (
    apply_competitor_shock,
    compute_demand,
    price_change_effect,
    update_market,
)
from app.engine.state import MarketState


def _market(**overrides) -> MarketState:
    defaults = dict(
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
    defaults.update(overrides)
    return MarketState(**defaults)


def test_demand_equals_base_when_neutral() -> None:
    market = _market()
    assert compute_demand(market, 1) == pytest.approx(100.0)


def test_price_rise_10_percent_elasticity() -> None:
    market = _market()
    raised = price_change_effect(market, 99.0 * 1.1)
    factor = compute_demand(raised, 1) / compute_demand(market, 1)
    assert factor == pytest.approx(1.1**-1.5, rel=1e-6)


def test_seasonality_doubles_july() -> None:
    market = _market(seasonality=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    assert compute_demand(market, 7) == pytest.approx(200.0)
    assert compute_demand(market, 19) == pytest.approx(200.0)
    assert compute_demand(market, 6) == pytest.approx(100.0)
    assert compute_demand(market, 8) == pytest.approx(100.0)


def test_competitor_pressure_halves_demand() -> None:
    market = _market(competitor_pressure=0.5)
    assert compute_demand(market, 1) == pytest.approx(50.0)


def test_demand_clamped_to_bounds() -> None:
    market = _market(competitor_pressure=0.8, brand_sentiment=0.0, seasonality=[10.0] * 12)
    demand = compute_demand(market, 1)
    assert demand >= 0.0
    assert demand <= market.market_size

    tiny = _market(base_demand=0.1, market_size=50000)
    assert compute_demand(tiny, 1) >= 0.0


def test_update_market_deterministic_and_clamped() -> None:
    a = _market()
    b = _market()
    for _ in range(24):
        a = update_market(a, random.Random(42), 1)
        b = update_market(b, random.Random(42), 1)
        assert a == b
        assert 0.0 <= a.competitor_pressure <= 0.8
        assert 0.0 <= a.brand_sentiment <= 1.0


def test_update_market_pressure_drifts_up() -> None:
    market = _market(competitor_pressure=0.0, brand_sentiment=0.5)
    rng = random.Random(1)
    for _ in range(12):
        market = update_market(market, rng, 1)
    assert market.competitor_pressure > 0.0


def test_market_size_grows() -> None:
    market = _market()
    grown = update_market(market, random.Random(0), 1)
    assert grown.market_size > market.market_size


def test_apply_competitor_shock() -> None:
    market = _market(competitor_pressure=0.4, brand_sentiment=0.5)
    shocked = apply_competitor_shock(market, 0.3, -0.1)
    assert shocked.competitor_pressure == pytest.approx(0.7)
    assert shocked.brand_sentiment == pytest.approx(0.4)
    # no mutation of input
    assert market.competitor_pressure == 0.4
    assert market.brand_sentiment == 0.5


def test_apply_competitor_shock_clamps() -> None:
    market = _market(competitor_pressure=0.7, brand_sentiment=0.9)
    shocked = apply_competitor_shock(market, 0.3, 0.3)
    assert shocked.competitor_pressure == pytest.approx(0.8)
    assert shocked.brand_sentiment == pytest.approx(1.0)
