"""Unit tests for the deep-report chart renderer (Day 04)."""

from __future__ import annotations

from typing import Any

from app.utils.charts import (
    cash_flow_curve,
    chart_sha256,
    cohort_percentile_gauge,
    kill_vector_bar,
    mc_distribution_histogram,
    tornado_chart,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _ticks() -> list[dict[str, Any]]:
    return [
        {"month": m, "cash_balance": 100000 - m * 3000, "revenue": m * 5000, "costs": 60000}
        for m in range(1, 25)
    ]


def _mc() -> dict[str, Any]:
    return {
        "survival_rate": 0.62,
        "n_runs": 100,
        "kill_vectors": {"financial": 22, "market": 10, "operational": 6},
        "runs_summary": [
            {"seed": i, "survived": i % 3 == 0, "lifespan_months": min(24, 5 + (i % 20))}
            for i in range(100)
        ],
    }


def test_cash_flow_curve_returns_png() -> None:
    png = cash_flow_curve(_ticks())
    assert png[:8] == PNG_MAGIC
    assert len(png) > 1000


def test_cash_flow_curve_accepts_legacy_cash_key() -> None:
    # The snippet-era tick shape used "cash"; the data pack uses
    # "cash_balance". Both must render.
    ticks = [
        {"month": i, "cash": 100000 - i * 3000, "revenue": 10000 + i * 500, "costs": 12000}
        for i in range(1, 13)
    ]
    png = cash_flow_curve(ticks)
    assert png[:8] == PNG_MAGIC


def test_mc_histogram_uses_runs_summary() -> None:
    png = mc_distribution_histogram(_mc())
    assert png[:8] == PNG_MAGIC


def test_kill_vector_bar_accepts_dict_shape() -> None:
    png = kill_vector_bar(_mc())
    assert png[:8] == PNG_MAGIC


def test_kill_vector_bar_accepts_list_shape() -> None:
    png = kill_vector_bar({"kill_vectors": [{"type": "market", "frequency": 0.5}]})
    assert png[:8] == PNG_MAGIC


def test_kill_vector_bar_empty_falls_back() -> None:
    png = kill_vector_bar({"kill_vectors": []})
    assert png[:8] == PNG_MAGIC


def test_kill_vector_bar_empty_dict_does_not_crash() -> None:
    png = kill_vector_bar({})
    assert png[:8] == PNG_MAGIC


def test_tornado_chart_with_and_without_data() -> None:
    data = [{"param": "churn", "low_delta": -0.12, "high_delta": 0.08}]
    assert tornado_chart(data)[:8] == PNG_MAGIC
    assert tornado_chart([])[:8] == PNG_MAGIC  # placeholder fallback


def test_gauge_returns_png() -> None:
    png = cohort_percentile_gauge(72.0, 84.0)
    assert png[:8] == PNG_MAGIC


def test_charts_are_deterministic() -> None:
    assert chart_sha256(cash_flow_curve(_ticks())) == chart_sha256(cash_flow_curve(_ticks()))
    assert chart_sha256(mc_distribution_histogram(_mc())) == chart_sha256(
        mc_distribution_histogram(_mc())
    )
