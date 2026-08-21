"""Day 04 tests: deep-report chart renderer (app.utils.charts).

Each chart function returns PNG bytes; render_charts_for_run writes the
four report charts to disk. Charts must be deterministic and never crash
on empty data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.deep_report.chart_builder import ChartBundle, render_charts_for_run
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


def test_cash_flow_curve_returns_png_bytes() -> None:
    png = cash_flow_curve(_ticks())
    assert png[:8] == PNG_MAGIC


def test_mc_histogram_returns_png_bytes() -> None:
    png = mc_distribution_histogram(_mc())
    assert png[:8] == PNG_MAGIC


def test_kill_vector_bar_returns_png_bytes() -> None:
    png = kill_vector_bar(_mc())
    assert png[:8] == PNG_MAGIC


def test_tornado_chart_returns_png_bytes() -> None:
    data = [{"param": "churn", "low_delta": -0.12, "high_delta": 0.08}]
    assert tornado_chart(data)[:8] == PNG_MAGIC
    assert tornado_chart([])[:8] == PNG_MAGIC  # placeholder fallback


def test_cohort_gauge_returns_png_bytes() -> None:
    png = cohort_percentile_gauge(72.0, 84.0)
    assert png[:8] == PNG_MAGIC


def test_charts_are_deterministic() -> None:
    # Same input → identical byte output for every chart.
    assert cash_flow_curve(_ticks()) == cash_flow_curve(_ticks())
    assert mc_distribution_histogram(_mc()) == mc_distribution_histogram(_mc())
    assert chart_sha256(kill_vector_bar(_mc())) == chart_sha256(kill_vector_bar(_mc()))


def test_render_charts_for_run_creates_files(tmp_path: Path) -> None:
    """render_charts_for_run writes all 4 report charts to the output dir."""
    bundle = render_charts_for_run(
        _ticks(), _mc(), "run-test", output_dir=str(tmp_path)
    )
    expected = {
        "cash_flow",
        "mc_histogram",
        "kill_vectors",
        "resilience_gauge",
    }
    assert set(bundle.charts.keys()) == expected
    for name in expected:
        assert (tmp_path / f"{name}.png").exists()


def test_chart_bundle_get_path(tmp_path: Path) -> None:
    bundle = ChartBundle(str(tmp_path))
    bundle.render_all(_ticks(), _mc())
    path = bundle.get_path("cash_flow")
    assert path is not None
    assert path.exists()
    assert path.stat().st_size > 1024


def test_empty_mc_does_not_crash() -> None:
    png = kill_vector_bar({})
    assert len(png) > 0
    assert png[:8] == PNG_MAGIC


def test_chart_files_are_valid_png_size(tmp_path: Path) -> None:
    """Each rendered PNG is a real image larger than 5KB."""
    bundle = render_charts_for_run(
        _ticks(), _mc(), "run-size", output_dir=str(tmp_path)
    )
    assert len(bundle.charts) == 4
    for path in bundle.charts.values():
        assert path.read_bytes()[:8] == PNG_MAGIC
        assert path.stat().st_size > 5 * 1024
