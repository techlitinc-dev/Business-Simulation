"""Tests for the pure financial calculator (spec §5 formulas)."""

import math

import pytest
from app.engine.financials import (
    apply_cash_flow,
    burn_rate,
    cac_payback_months,
    cash_conversion_cycle,
    compute_costs,
    compute_revenue,
    inventory_turnover,
    ltv,
    monthly_payroll,
    net_revenue_retention,
    runway_months,
)
from app.engine.state import FinancialState, RevenueStream, TeamMember


def _fin(**overrides) -> FinancialState:
    defaults = dict(
        cash=100000.0,
        mrr=0.0,
        arr=0.0,
        monthly_burn=0.0,
        fixed_monthly=35000.0,
        variable_per_unit=12.0,
        ar_days=30,
        ap_days=30,
        gross_margin=0.8,
        team=[
            TeamMember("CEO/Founder", 80000.0, 0),
            TeamMember("Engineer", 120000.0, 3),
        ],
    )
    defaults.update(overrides)
    return FinancialState(**defaults)


def test_ltv() -> None:
    assert ltv(99, 0.8, 0.05) == 1584.0


def test_ltv_zero_churn_raises() -> None:
    with pytest.raises(ValueError, match="churn"):
        ltv(99, 0.8, 0.0)


def test_cac_payback_months() -> None:
    assert cac_payback_months(850, 99, 0.8) == pytest.approx(10.7316, abs=0.01)


def test_runway_months() -> None:
    assert runway_months(500000, 45000) == pytest.approx(11.1111, abs=0.01)


def test_runway_zero_burn_is_inf() -> None:
    assert runway_months(100, -5) == math.inf
    assert runway_months(100, 0) == math.inf


def test_net_revenue_retention() -> None:
    assert net_revenue_retention(10000, 2000, 500, 1000) == pytest.approx(1.05)


def test_net_revenue_retention_zero_mrr_raises() -> None:
    with pytest.raises(ValueError, match="mrr"):
        net_revenue_retention(0, 100, 50, 50)


def test_inventory_turnover() -> None:
    assert inventory_turnover(1000, 200) == 5.0


def test_cash_conversion_cycle() -> None:
    assert cash_conversion_cycle(30, 45, 20) == 55.0


def test_monthly_payroll_honors_hire_month() -> None:
    team = [
        TeamMember("A", 120000.0, 0),
        TeamMember("B", 120000.0, 3),
        TeamMember("C", 60000.0, 6),
    ]
    assert monthly_payroll(team, 0) == pytest.approx(10000.0)
    assert monthly_payroll(team, 2) == pytest.approx(10000.0)
    assert monthly_payroll(team, 3) == pytest.approx(20000.0)
    assert monthly_payroll(team, 6) == pytest.approx(25000.0)


def test_compute_revenue() -> None:
    stream = RevenueStream("s", "Subscription", 99.0, 500, 2400.0, 850.0, 0.05, customers=100)
    ending, revenue = compute_revenue(10, 5, stream)
    assert ending == 105
    assert revenue == pytest.approx(105 * 99.0)


def test_compute_revenue_never_negative() -> None:
    stream = RevenueStream("s", "Subscription", 99.0, 500, 2400.0, 850.0, 0.05, customers=5)
    ending, revenue = compute_revenue(0, 100, stream)
    assert ending == 0
    assert revenue == 0.0


def test_compute_costs_total() -> None:
    fin = _fin()
    costs = compute_costs(fin, units_sold=500, marketing_spend=2000.0, month=4)
    assert costs["fixed"] == 35000.0
    assert costs["payroll"] == pytest.approx(80000 / 12 + 120000 / 12)
    assert costs["variable"] == pytest.approx(12 * 500)
    assert costs["operational"] == 2000.0
    expected_total = costs["fixed"] + costs["payroll"] + costs["variable"] + costs["operational"]
    assert costs["total"] == pytest.approx(expected_total)


def test_apply_cash_flow_is_pure_with_ar_30() -> None:
    fin = _fin(cash=500000.0, accounts_receivable=0.0)
    result = apply_cash_flow(fin, revenue=10000.0, total_costs=45000.0)
    # Original unchanged
    assert fin.cash == 500000.0
    assert fin.accounts_receivable == 0.0
    assert fin.mrr == 0.0
    # New state: previous AR (0) hits cash, this month's revenue becomes AR
    assert result.cash == pytest.approx(500000.0 - 45000.0)
    assert result.accounts_receivable == pytest.approx(10000.0)
    assert result.mrr == pytest.approx(10000.0)
    assert result.arr == pytest.approx(120000.0)
    assert result.monthly_burn == pytest.approx(45000.0 - 10000.0)


def test_apply_cash_flow_ar_0_recognizes_immediately() -> None:
    fin = _fin(cash=500000.0, ar_days=0, accounts_receivable=0.0)
    result = apply_cash_flow(fin, revenue=10000.0, total_costs=45000.0)
    assert result.cash == pytest.approx(500000.0 + 10000.0 - 45000.0)
    assert result.accounts_receivable == 0.0


def test_burn_rate_signed() -> None:
    assert burn_rate(10000, 45000) == 35000.0
    assert burn_rate(10000, 8000) == -2000.0
