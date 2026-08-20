from __future__ import annotations

import tempfile
from pathlib import Path

from app.services.whatif.schemas import SweepResult
from app.utils.charts import survival_line_chart, sweep_heatmap, tornado_chart


class WhatIfChartBundle:
    def __init__(self, output_dir: str) -> None:
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
        output_dir = tempfile.mkdtemp(
            prefix=f"whatif_charts_{sweep_result.blueprint_id}_"
        )

    bundle = WhatIfChartBundle(output_dir)
    grid_dicts = [pt.model_dump() for pt in sweep_result.grid]

    # Heatmap
    bundle._write("heatmap", sweep_heatmap(grid_dicts, sweep_result.param))

    # Survival line chart
    bundle._write("survival_line", survival_line_chart(grid_dicts, sweep_result.param))

    # Tornado: treat this single param as one bar. The deltas are survival-rate
    # differences across the grid (sweep has no per-parameter low/high deltas).
    if len(sweep_result.grid) >= 2:
        first = sweep_result.grid[0].survival_rate
        last = sweep_result.grid[-1].survival_rate
        midpoint = sweep_result.grid[len(sweep_result.grid) // 2].survival_rate
        sensitivity = [
            {
                "param": sweep_result.param,
                "low_delta": last - first,
                "high_delta": first - midpoint,
            }
        ]
        bundle._write("tornado", tornado_chart(sensitivity))

    return bundle
