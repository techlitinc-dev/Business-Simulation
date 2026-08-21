"""Day 04 tests: deep-report chart renderer (app.utils.charts).

Covers the four report charts (cash flow, MC histogram, kill vectors,
resilience gauge) plus determinism, empty-data safety, and the
render_charts_for_run bundle that writes them to disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.deep_report.chart_builder import render_charts_for_run
from app.utils.charts import (
    cash_flow_curve,
    chart_sha256,
    cohort_percentile_gauge,
    kill_vector_bar,
    mc_distribution_histogram,
    survival_line_chart,
    sweep_heatmap,
    tornado_chart,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _grid_points() -> list[dict[str, Any]]:
    return [
        {"param_value": 0.03, "survival_rate": 1.0, "p25_runway": 24.0, "p75_runway": 24.0},
        {"param_value": 0.05, "survival_rate": 0.8, "p25_runway": 18.0, "p75_runway": 24.0},
        {"param_value": 0.07, "survival_rate": 0.4, "p25_runway": 12.0, "p75_runway": 20.0},
        {"param_value": 0.10, "survival_rate": 0.1, "p25_runway": 8.0, "p75_runway": 14.0},
    ]


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


def test_kill_vector_bar_empty_data_does_not_crash() -> None:
    # Empty dict and empty list both fall back to a "No data" bar.
    assert kill_vector_bar({})[:8] == PNG_MAGIC
    assert kill_vector_bar({"kill_vectors": []})[:8] == PNG_MAGIC


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
    assert chart_sha256(sweep_heatmap(_grid_points(), "churn")) == chart_sha256(
        sweep_heatmap(_grid_points(), "churn")
    )
    assert chart_sha256(survival_line_chart(_grid_points(), "churn")) == chart_sha256(
        survival_line_chart(_grid_points(), "churn")
    )


def test_render_charts_for_run_bundle(tmp_path: Path) -> None:
    """render_charts_for_run writes all 4 report charts to disk."""
    bundle = render_charts_for_run(
        _ticks(), _mc(), "manual-test-run", output_dir=str(tmp_path)
    )
    assert set(bundle.charts.keys()) == {
        "cash_flow",
        "mc_histogram",
        "kill_vectors",
        "resilience_gauge",
    }
    for path in bundle.charts.values():
        assert path.exists()
        assert path.read_bytes()[:8] == PNG_MAGIC
