"""Unit tests for the what-if chart visualizer (Day 08)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.whatif.schemas import SweepGridPoint, SweepResult
from app.services.whatif.visualizer import render_sweep_charts
from app.utils.charts import survival_line_chart, sweep_heatmap

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _sweep_result() -> SweepResult:
    return SweepResult(
        blueprint_id="bp_1",
        param="revenue_engine.streams.0.churn_monthly",
        grid=[
            SweepGridPoint(
                param_value=0.03, survival_rate=1.0,
                median_runway=24.0, p25_runway=24.0, p75_runway=24.0,
            ),
            SweepGridPoint(
                param_value=0.05, survival_rate=0.8,
                median_runway=20.0, p25_runway=18.0, p75_runway=24.0,
            ),
            SweepGridPoint(
                param_value=0.08, survival_rate=0.3,
                median_runway=14.0, p25_runway=12.0, p75_runway=18.0,
            ),
            SweepGridPoint(
                param_value=0.12, survival_rate=0.0,
                median_runway=10.0, p25_runway=9.0, p75_runway=12.0,
            ),
        ],
    )


def test_render_sweep_charts_writes_three_pngs(tmp_path: Path) -> None:
    bundle = render_sweep_charts(_sweep_result(), output_dir=str(tmp_path))
    assert set(bundle.charts.keys()) == {"heatmap", "survival_line", "tornado"}
    for path in bundle.charts.values():
        assert path.exists()
        assert path.read_bytes()[:8] == PNG_MAGIC


def test_render_sweep_charts_uses_tempdir_when_no_output_dir() -> None:
    bundle = render_sweep_charts(_sweep_result())
    assert len(bundle.charts) == 3
    for path in bundle.charts.values():
        assert path.exists()


def _grid_dicts() -> list[dict[str, Any]]:
    return [pt.model_dump() for pt in _sweep_result().grid]


def test_heatmap_returns_png_bytes() -> None:
    result = sweep_heatmap(_grid_dicts(), "monthly_churn")
    assert result[:4] == b"\x89PNG"


def test_survival_line_chart_returns_png_bytes() -> None:
    result = survival_line_chart(_grid_dicts(), "monthly_churn")
    assert result[:4] == b"\x89PNG"


def test_heatmap_is_deterministic() -> None:
    grid = _grid_dicts()
    assert sweep_heatmap(grid, "monthly_churn") == sweep_heatmap(grid, "monthly_churn")


def test_heatmap_with_single_point_does_not_crash() -> None:
    grid = [{"param_value": 0.05, "survival_rate": 0.6, "p25_runway": 15, "p75_runway": 22}]
    result = sweep_heatmap(grid, "price")
    assert isinstance(result, bytes)
