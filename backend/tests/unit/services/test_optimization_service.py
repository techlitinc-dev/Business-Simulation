"""Unit tests for the counter-factual optimization service (T31)."""

import json
from pathlib import Path

import pytest
from app.services.optimization_service import (
    TWEAKS,
    apply_tweak,
    estimate_survival_delta,
    measure_all_tweaks,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _payload() -> dict:
    return json.loads((FIXTURES / "blueprint_golden.json").read_text())


def test_apply_churn_tweak() -> None:
    payload = apply_tweak(_payload(), next(t for t in TWEAKS if t.key == "churn"))
    stream = payload["revenue_engine"]["streams"][0]
    assert stream["churn_monthly"] == pytest.approx(0.05 * 0.8)
    # Everything else untouched.
    assert payload["cost_structure"]["fixed_monthly"] == 50000


def test_apply_price_tweak() -> None:
    payload = apply_tweak(_payload(), next(t for t in TWEAKS if t.key == "price"))
    assert payload["revenue_engine"]["streams"][0]["price_point"] == pytest.approx(99 * 1.1)


def test_apply_fixed_monthly_tweak() -> None:
    payload = apply_tweak(
        _payload(), next(t for t in TWEAKS if t.key == "fixed_monthly")
    )
    assert payload["cost_structure"]["fixed_monthly"] == pytest.approx(50000 * 0.85)
    assert payload["cost_structure"]["burn_rate_month_1"] == pytest.approx(60000 * 0.85)


def test_apply_starting_capital_tweak() -> None:
    payload = apply_tweak(
        _payload(), next(t for t in TWEAKS if t.key == "starting_capital")
    )
    assert payload["financials"]["starting_capital"] == pytest.approx(380000 * 1.25)


def test_delta_deterministic() -> None:
    payload = _payload()
    tweak = next(t for t in TWEAKS if t.key == "churn")
    a = estimate_survival_delta(payload, tweak, n_runs=20, seed=42)
    b = estimate_survival_delta(payload, tweak, n_runs=20, seed=42)
    assert a == b


def test_measure_all_tweaks_returns_six() -> None:
    results = measure_all_tweaks(_payload(), n_runs=10, seed=7)
    assert len(results) == 6
    keys = [r.tweak_key for r in results]
    assert set(keys) == {
        "churn", "cac", "price", "fixed_monthly", "starting_capital",
        "client_concentration",
    }
    for r in results:
        assert -100.0 <= r.delta_pp <= 100.0
        assert 0.0 <= r.baseline_survival <= 1.0
        assert 0.0 <= r.tweaked_survival <= 1.0
