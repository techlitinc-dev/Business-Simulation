from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from app.utils.charts import (
    cash_flow_curve,
    cohort_percentile_gauge,
    kill_vector_bar,
    mc_distribution_histogram,
    tornado_chart,
)


class ChartBundle:
    """Holds paths to rendered PNG chart files for one report."""

    def __init__(self, output_dir: str) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.charts: dict[str, Path] = {}

    def _write(self, name: str, png_bytes: bytes) -> Path:
        path = self.output_dir / f"{name}.png"
        path.write_bytes(png_bytes)
        self.charts[name] = path
        return path

    def render_all(
        self,
        tick_logs: list[dict[str, Any]],
        mc_aggregates: dict[str, Any],
        sensitivity_results: list[dict[str, Any]] | None = None,
        resilience_score: float = 0,
        cohort_percentile: float = 50,
    ) -> ChartBundle:
        if tick_logs:
            self._write("cash_flow", cash_flow_curve(tick_logs))
        if mc_aggregates:
            self._write("mc_histogram", mc_distribution_histogram(mc_aggregates))
            self._write("kill_vectors", kill_vector_bar(mc_aggregates))
        if sensitivity_results:
            self._write("tornado", tornado_chart(sensitivity_results))
        self._write(
            "resilience_gauge",
            cohort_percentile_gauge(resilience_score, cohort_percentile),
        )
        return self

    def get_path(self, name: str) -> Path | None:
        return self.charts.get(name)


def render_charts_for_run(
    tick_logs: list[dict[str, Any]],
    mc_aggregates: dict[str, Any],
    run_id: str,
    output_dir: str | None = None,
) -> ChartBundle:
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix=f"report_charts_{run_id}_")
    bundle = ChartBundle(output_dir)
    bundle.render_all(tick_logs=tick_logs, mc_aggregates=mc_aggregates)
    return bundle
