"""Pure financial math for the engine (spec §5).

No classes, no state mutation: every function takes plain numbers and/or
engine dataclasses and returns numbers or a new ``FinancialState``.
"""

from __future__ import annotations

import math
from dataclasses import replace

from app.engine.state import FinancialState, RevenueStream, TeamMember


def ltv(arpu: float, gross_margin: float, churn_monthly: float) -> float:
    """Spec formula: (ARPU x Gross Margin) / Monthly Churn Rate."""
    if churn_monthly <= 0:
        raise ValueError("churn_monthly must be > 0")
    return (arpu * gross_margin) / churn_monthly


def cac_payback_months(cac: float, arpu: float, gross_margin: float) -> float:
    """Spec formula: CAC / (ARPU x Gross Margin)."""
    return cac / (arpu * gross_margin)


def runway_months(cash: float, monthly_burn: float) -> float:
    """Spec formula: Cash Balance / Monthly Burn Rate (inf when burn <= 0)."""
    if monthly_burn <= 0:
        return math.inf
    return cash / monthly_burn


def net_revenue_retention(
    starting_mrr: float, expansion: float, contraction: float, churned: float
) -> float:
    """Spec formula: (Starting MRR + Expansion - Contraction - Churn) / Starting MRR."""
    if starting_mrr <= 0:
        raise ValueError("starting_mrr must be > 0")
    return (starting_mrr + expansion - contraction - churned) / starting_mrr


def inventory_turnover(cogs: float, average_inventory: float) -> float:
    """Spec formula: COGS / Average Inventory."""
    return cogs / average_inventory


def cash_conversion_cycle(dio: float, dso: float, dpo: float) -> float:
    """Spec formula: DIO + DSO - DPO."""
    return dio + dso - dpo


def monthly_payroll(team: list[TeamMember], month: int) -> float:
    """Sum of salary_annual / 12 for members hired by the given month."""
    return sum(member.salary_annual / 12 for member in team if member.hire_month <= month)


def compute_revenue(
    new_customers: int, churned_customers: int, stream: RevenueStream
) -> tuple[int, float]:
    """Return (ending_customers, recognized_revenue) for a subscription stream."""
    ending_customers = max(0, stream.customers + new_customers - churned_customers)
    recognized_revenue = ending_customers * stream.price_point
    return ending_customers, recognized_revenue


def compute_costs(
    fin: FinancialState, units_sold: int, marketing_spend: float, month: int
) -> dict[str, float]:
    """Spec §5 step 2: fixed + payroll + variable + operational costs."""
    fixed = fin.fixed_monthly
    payroll = monthly_payroll(fin.team, month)
    variable = fin.variable_per_unit * units_sold
    operational = marketing_spend
    return {
        "fixed": fixed,
        "payroll": payroll,
        "variable": variable,
        "operational": operational,
        "total": fixed + payroll + variable + operational,
    }


def burn_rate(revenue: float, total_costs: float) -> float:
    """Spec: total_costs - revenue (negative means profitable)."""
    return total_costs - revenue


def apply_cash_flow(fin: FinancialState, revenue: float, total_costs: float) -> FinancialState:
    """Spec §5 step 3: apply the month's cash movement, returning a NEW state."""
    if fin.ar_days == 0:
        cash = fin.cash + revenue - total_costs
        accounts_receivable = 0.0
    else:
        # Net-30 AR default: this month's revenue lands as cash next month.
        cash = fin.cash + fin.accounts_receivable - total_costs
        accounts_receivable = revenue
    new_burn = burn_rate(revenue, total_costs)
    return replace(
        fin,
        cash=cash,
        mrr=revenue,
        arr=revenue * 12,
        monthly_burn=new_burn,
        accounts_receivable=accounts_receivable,
    )
