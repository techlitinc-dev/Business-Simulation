"""Unit tests for the deep-report chart builder (Day 04)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.deep_report.chart_builder import (
    ChartBundle,
    render_charts_for_run,
)


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
            {"seed": i, "survived": True, "lifespan_months": 20} for i in range(100)
        ],
    }


def test_render_charts_for_run_writes_pngs(tmp_path: Path) -> None:
    bundle = render_charts_for_run(_ticks(), _mc(), "run_abc", output_dir=str(tmp_path))
    assert bundle.get_path("cash_flow") is not None
    assert bundle.get_path("mc_histogram") is not None
    assert bundle.get_path("kill_vectors") is not None
    assert bundle.get_path("resilience_gauge") is not None
    for path in bundle.charts.values():
        assert path.exists()
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_all_includes_tornado_when_provided(tmp_path: Path) -> None:
    bundle = ChartBundle(str(tmp_path))
    bundle.render_all(
        _ticks(),
        _mc(),
        sensitivity_results=[{"param": "churn", "low_delta": -0.1, "high_delta": 0.05}],
    )
    assert bundle.get_path("tornado") is not None


def test_render_all_empty_data_still_renders_gauge(tmp_path: Path) -> None:
    bundle = ChartBundle(str(tmp_path))
    bundle.render_all([], {})
    assert bundle.get_path("resilience_gauge") is not None
    assert bundle.get_path("cash_flow") is None
    assert bundle.get_path("mc_histogram") is None


def test_get_path_missing_returns_none(tmp_path: Path) -> None:
    bundle = ChartBundle(str(tmp_path))
    assert bundle.get_path("does_not_exist") is None


def test_render_charts_for_run_uses_tempdir_when_no_output_dir() -> None:
    bundle = render_charts_for_run(_ticks(), _mc(), "run_tmp")
    assert bundle.get_path("cash_flow") is not None
