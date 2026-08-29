# Day 09 — F-06: Tornado Chart + Heatmap Charts

## Feature
F-06: What-If Lab & Sensitivity Sweeps

## Goal
Add `tornado_chart()` and `heatmap()` server-side renderers to `charts.py`, and create `visualizer.py` that orchestrates charts from sweep results. These charts are also fed into section 14 of the F-01 report.

## Prerequisites
- Day 08 complete (sweep.py, schemas.py)
- Day 04 complete (charts.py with existing chart helpers)

---

## Step 1 — Add `heatmap()` to `backend/app/utils/charts.py`

```python
def sweep_heatmap(grid_points: list[dict], param_name: str) -> bytes:
    """
    2D heatmap: X=param_value, color=survival_rate.
    grid_points: list of {"param_value": float, "survival_rate": float}
    """
    _apply_style()
    import numpy as np

    values = [pt["param_value"] for pt in grid_points]
    survivals = [pt["survival_rate"] * 100 for pt in grid_points]

    fig, ax = plt.subplots(figsize=(10, 2.5))
    # Create 1-row heatmap
    data = np.array([survivals])
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn", vmin=0, vmax=100)
    ax.set_xticks(range(len(values)))
    ax.set_xticklabels([f"{v:.3f}" for v in values], rotation=45, ha="right", fontsize=8)
    ax.set_yticks([])
    ax.set_title(f"Survival Rate vs {param_name.replace('_', ' ').title()}", fontsize=11)

    # Annotate cells
    for i, s in enumerate(survivals):
        ax.text(i, 0, f"{s:.0f}%", ha="center", va="center",
                fontsize=9, color="black" if 30 < s < 75 else "white", fontweight="bold")

    plt.colorbar(im, ax=ax, orientation="horizontal", pad=0.4, label="Survival Rate (%)")
    fig.tight_layout()
    return _save_to_bytes(fig)


def survival_line_chart(grid_points: list[dict], param_name: str) -> bytes:
    """
    Line chart of survival rate across parameter values.
    Shows P25/P75 band as shaded area.
    """
    _apply_style()
    fig, ax = plt.subplots(figsize=(9, 4))
    values = [pt["param_value"] for pt in grid_points]
    survival = [pt["survival_rate"] * 100 for pt in grid_points]
    p25 = [pt.get("p25_runway", 0) for pt in grid_points]
    p75 = [pt.get("p75_runway", 24) for pt in grid_points]

    ax.plot(values, survival, color="#3b82f6", linewidth=2.5, marker="o", markersize=5, label="Survival Rate %")
    ax.fill_between(values, p25, p75, alpha=0.15, color="#3b82f6", label="P25-P75 Runway")
    ax.axhline(50, color="#eab308", linewidth=1, linestyle="--", label="50% threshold")

    ax.set_xlabel(param_name.replace("_", " ").title())
    ax.set_ylabel("Survival Rate (%)")
    ax.set_title(f"Survival Rate vs {param_name.replace('_', ' ').title()}")
    ax.legend(facecolor="#1e293b", edgecolor="#334155")
    ax.grid(True, alpha=0.3)
    return _save_to_bytes(fig)
```

---

## Step 2 — Create `backend/app/services/whatif/visualizer.py`

```python
from __future__ import annotations
import tempfile
from pathlib import Path
from app.services.whatif.schemas import SweepResult
from app.utils.charts import (
    tornado_chart, sweep_heatmap, survival_line_chart
)


class WhatIfChartBundle:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.charts: dict[str, Path] = {}

    def _write(self, name: str, png_bytes: bytes) -> Path:
        path = self.output_dir / f"{name}.png"
        path.write_bytes(png_bytes)
        self.charts[name] = path
        return path


def render_sweep_charts(
    sweep_result: SweepResult,
    output_dir: str | None = None,
) -> WhatIfChartBundle:
    """
    Render heatmap, survival line chart, and tornado chart from a SweepResult.
    Returns a bundle of PNG paths.
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix=f"whatif_charts_{sweep_result.blueprint_id}_")

    bundle = WhatIfChartBundle(output_dir)
    grid_dicts = [pt.model_dump() for pt in sweep_result.grid]

    # Heatmap
    bundle._write("heatmap", sweep_heatmap(grid_dicts, sweep_result.param))

    # Survival line chart
    bundle._write("survival_line", survival_line_chart(grid_dicts, sweep_result.param))

    # Tornado: treat this single param as one bar
    sensitivity = [{
        "param": sweep_result.param,
        "low_delta": sweep_result.grid[-1].survival_rate - sweep_result.grid[0].survival_rate,
        "high_delta": sweep_result.grid[0].survival_rate - sweep_result.grid[len(sweep_result.grid) // 2].survival_rate,
    }]
    bundle._write("tornado", tornado_chart(sensitivity))

    return bundle
```

---

## Step 3 — Test file

`backend/tests/unit/whatif/test_visualizer.py`:

```python
import pytest
from app.services.whatif.schemas import SweepResult, SweepGridPoint
from app.services.whatif.visualizer import render_sweep_charts
from app.utils.charts import sweep_heatmap, survival_line_chart


MOCK_SWEEP = SweepResult(
    blueprint_id="bp_001",
    param="monthly_churn",
    grid=[
        SweepGridPoint(param_value=0.02, survival_rate=0.90, median_runway=24, p25_runway=22, p75_runway=24),
        SweepGridPoint(param_value=0.05, survival_rate=0.65, median_runway=20, p25_runway=16, p75_runway=24),
        SweepGridPoint(param_value=0.08, survival_rate=0.40, median_runway=15, p25_runway=10, p75_runway=20),
        SweepGridPoint(param_value=0.11, survival_rate=0.15, median_runway=10, p25_runway=6,  p75_runway=16),
    ]
)


def test_heatmap_returns_png_bytes():
    grid = [pt.model_dump() for pt in MOCK_SWEEP.grid]
    result = sweep_heatmap(grid, "monthly_churn")
    assert result[:4] == b'\x89PNG'


def test_survival_line_chart_returns_png_bytes():
    grid = [pt.model_dump() for pt in MOCK_SWEEP.grid]
    result = survival_line_chart(grid, "monthly_churn")
    assert result[:4] == b'\x89PNG'


def test_render_sweep_charts_creates_three_files(tmp_path):
    bundle = render_sweep_charts(MOCK_SWEEP, str(tmp_path))
    assert (tmp_path / "heatmap.png").exists()
    assert (tmp_path / "survival_line.png").exists()
    assert (tmp_path / "tornado.png").exists()


def test_render_sweep_charts_returns_bundle_with_all_keys(tmp_path):
    bundle = render_sweep_charts(MOCK_SWEEP, str(tmp_path))
    assert "heatmap" in bundle.charts
    assert "survival_line" in bundle.charts
    assert "tornado" in bundle.charts


def test_heatmap_is_deterministic(tmp_path):
    grid = [pt.model_dump() for pt in MOCK_SWEEP.grid]
    r1 = sweep_heatmap(grid, "monthly_churn")
    r2 = sweep_heatmap(grid, "monthly_churn")
    assert r1 == r2


def test_heatmap_with_single_point_does_not_crash():
    grid = [{"param_value": 0.05, "survival_rate": 0.6, "p25_runway": 15, "p75_runway": 22}]
    result = sweep_heatmap(grid, "price")
    assert isinstance(result, bytes)
```

---

## Step 4 — Wire into Section 14 of Deep Report

In `backend/app/services/deep_report/data_pack.py`, update the `DataInputKey.MC_AGGREGATES` section to also store sweep sensitivity data if available:

```python
# When building data pack for section 14 (Sensitivity Analysis):
# If a sweep result is cached for this run, include it in the data pack.
# This is optional for Day 09 — add as a TODO comment for now.
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/whatif/test_visualizer.py -v
cd backend && ruff check app/services/whatif/visualizer.py app/utils/charts.py
```
