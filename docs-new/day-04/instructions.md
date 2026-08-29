# Day 04 — F-01: Chart Generation (Server-Side, Deterministic)

## Feature
F-01: Deep-Dive Report Engine

## Goal
Implement server-side chart renderers using matplotlib. All charts render from engine/tick data — zero LLM involvement. Charts are saved as PNG files and embedded in the report PDF. Five chart types: cash-flow curve, MC distribution histogram, tornado placeholder, kill-vector bar chart, cohort percentile gauge.

## Prerequisites
- Day 01–03 complete
- `matplotlib` available in requirements.txt (add if missing)
- `seaborn` optional (add for styling)

---

## Step 1 — Add matplotlib to requirements.txt

```
matplotlib==3.9.0
seaborn==0.13.2
```

---

## Step 2 — Create `backend/app/utils/charts.py`

```python
"""
Server-side chart rendering for the Deep-Dive Report Engine.
All charts are deterministic (same data → same PNG bytes).
No LLM involvement.
"""
from __future__ import annotations
import io
import hashlib
from pathlib import Path
from typing import Any
import matplotlib
matplotlib.use("Agg")  # headless, no display required
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


CHART_STYLE = {
    "figure.facecolor": "#0f172a",
    "axes.facecolor": "#1e293b",
    "axes.edgecolor": "#334155",
    "axes.labelcolor": "#94a3b8",
    "xtick.color": "#94a3b8",
    "ytick.color": "#94a3b8",
    "text.color": "#e2e8f0",
    "grid.color": "#1e3a5f",
    "grid.alpha": 0.3,
}


def _apply_style():
    plt.rcParams.update(CHART_STYLE)


def _save_to_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def cash_flow_curve(tick_logs: list[dict]) -> bytes:
    """Line chart: cash, revenue, costs over time."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(10, 4))
    months = [t["month"] for t in tick_logs]
    ax.plot(months, [t["cash"] for t in tick_logs], label="Cash", color="#3b82f6", linewidth=2)
    ax.plot(months, [t["revenue"] for t in tick_logs], label="Revenue", color="#22c55e", linewidth=1.5)
    ax.plot(months, [t["costs"] for t in tick_logs], label="Costs", color="#ef4444", linewidth=1.5, linestyle="--")
    ax.axhline(0, color="#f59e0b", linewidth=0.8, linestyle=":")
    ax.set_xlabel("Month")
    ax.set_ylabel("Amount ($)")
    ax.set_title("Cash Flow Over 24 Months")
    ax.legend(facecolor="#1e293b", edgecolor="#334155")
    ax.grid(True, alpha=0.3)
    return _save_to_bytes(fig)


def mc_distribution_histogram(mc_aggregates: dict) -> bytes:
    """Histogram of survival outcomes from Monte Carlo runs."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(8, 4))
    lifespan_dist = mc_aggregates.get("lifespan_distribution", [])
    if not lifespan_dist:
        lifespan_dist = list(range(1, 25))  # placeholder
    ax.hist(lifespan_dist, bins=24, color="#6366f1", edgecolor="#4338ca", alpha=0.85)
    survival_rate = mc_aggregates.get("survival_rate", 0)
    ax.set_title(f"Simulated Business Lifespan Distribution (Survival: {survival_rate:.0%})")
    ax.set_xlabel("Months Survived")
    ax.set_ylabel("Number of Runs")
    ax.grid(True, alpha=0.3)
    return _save_to_bytes(fig)


def kill_vector_bar(mc_aggregates: dict) -> bytes:
    """Horizontal bar chart of top failure causes."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(8, 4))
    kill_vectors = mc_aggregates.get("kill_vectors", [])
    if not kill_vectors:
        kill_vectors = [{"type": "No data", "frequency": 1.0}]
    labels = [kv.get("type", "unknown").replace("_", " ").title() for kv in kill_vectors]
    values = [kv.get("frequency", 0) * 100 for kv in kill_vectors]
    colors = ["#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e"]
    ax.barh(labels, values, color=colors[:len(labels)])
    ax.set_xlabel("% of Failed Runs")
    ax.set_title("Top Kill Vectors")
    ax.grid(True, axis="x", alpha=0.3)
    return _save_to_bytes(fig)


def tornado_chart(sensitivity_results: list[dict]) -> bytes:
    """
    Tornado chart: impact of each parameter on survival delta.
    sensitivity_results: [{"param": str, "low_delta": float, "high_delta": float}]
    """
    _apply_style()
    if not sensitivity_results:
        sensitivity_results = [{"param": "churn_rate", "low_delta": -0.12, "high_delta": 0.08}]
    fig, ax = plt.subplots(figsize=(9, max(4, len(sensitivity_results) * 0.6)))
    params = [r["param"].replace("_", " ").title() for r in sensitivity_results]
    low_deltas = [r.get("low_delta", 0) * 100 for r in sensitivity_results]
    high_deltas = [r.get("high_delta", 0) * 100 for r in sensitivity_results]
    y = np.arange(len(params))
    ax.barh(y, [abs(l) for l in low_deltas], left=[min(l, 0) for l in low_deltas],
            color="#ef4444", alpha=0.8, label="Negative impact")
    ax.barh(y, high_deltas, color="#22c55e", alpha=0.8, label="Positive impact")
    ax.set_yticks(y)
    ax.set_yticklabels(params)
    ax.axvline(0, color="#94a3b8", linewidth=0.8)
    ax.set_xlabel("Survival Rate Change (%)")
    ax.set_title("Parameter Sensitivity — Tornado Chart")
    ax.legend(facecolor="#1e293b", edgecolor="#334155")
    return _save_to_bytes(fig)


def cohort_percentile_gauge(score: float, percentile: float) -> bytes:
    """Semicircle gauge showing score and cohort percentile."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(6, 3), subplot_kw={"projection": "polar"})
    theta = np.linspace(0, np.pi, 100)
    ax.plot(theta, np.ones(100), color="#334155", linewidth=8)
    filled = np.linspace(0, np.pi * (score / 100), 100)
    color = "#22c55e" if score >= 70 else "#eab308" if score >= 50 else "#ef4444"
    ax.plot(filled, np.ones(len(filled)), color=color, linewidth=8)
    ax.set_ylim(0, 1.5)
    ax.set_theta_zero_location("W")
    ax.set_theta_direction(-1)
    ax.axis("off")
    ax.text(0, 0, f"{score:.0f}", ha="center", va="center", fontsize=28, color=color, fontweight="bold")
    ax.set_title(f"Resilience Score — {percentile:.0f}th Percentile vs. Peers", pad=15)
    return _save_to_bytes(fig)
```

---

## Step 3 — Create `chart_builder.py`

`backend/app/services/deep_report/chart_builder.py`:

```python
from __future__ import annotations
import tempfile
import os
from pathlib import Path
from typing import Any
from app.utils.charts import (
    cash_flow_curve, mc_distribution_histogram,
    kill_vector_bar, tornado_chart, cohort_percentile_gauge,
)


class ChartBundle:
    """Holds paths to rendered PNG chart files for one report."""
    def __init__(self, output_dir: str):
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
        tick_logs: list[dict],
        mc_aggregates: dict,
        sensitivity_results: list[dict] | None = None,
        resilience_score: float = 0,
        cohort_percentile: float = 50,
    ) -> "ChartBundle":
        if tick_logs:
            self._write("cash_flow", cash_flow_curve(tick_logs))
        if mc_aggregates:
            self._write("mc_histogram", mc_distribution_histogram(mc_aggregates))
            self._write("kill_vectors", kill_vector_bar(mc_aggregates))
        if sensitivity_results:
            self._write("tornado", tornado_chart(sensitivity_results))
        self._write("resilience_gauge", cohort_percentile_gauge(resilience_score, cohort_percentile))
        return self

    def get_path(self, name: str) -> Path | None:
        return self.charts.get(name)


def render_charts_for_run(
    tick_logs: list[dict],
    mc_aggregates: dict,
    run_id: str,
    output_dir: str | None = None,
) -> ChartBundle:
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix=f"report_charts_{run_id}_")
    bundle = ChartBundle(output_dir)
    bundle.render_all(tick_logs=tick_logs, mc_aggregates=mc_aggregates)
    return bundle
```

---

## Step 4 — Test file

`backend/tests/unit/deep_report/test_charts.py`:

```python
import pytest
from app.utils.charts import (
    cash_flow_curve, mc_distribution_histogram,
    kill_vector_bar, tornado_chart, cohort_percentile_gauge,
)
from app.services.deep_report.chart_builder import render_charts_for_run

SAMPLE_TICKS = [{"month": i, "cash": 100000 - i*3000, "revenue": 10000 + i*500, "costs": 12000} for i in range(1, 13)]
SAMPLE_MC = {"survival_rate": 0.68, "lifespan_distribution": list(range(6, 25)), "kill_vectors": [{"type": "cash_out", "frequency": 0.4}]}


def test_cash_flow_curve_returns_png_bytes():
    result = cash_flow_curve(SAMPLE_TICKS)
    assert isinstance(result, bytes)
    assert result[:4] == b'\x89PNG'


def test_mc_histogram_returns_png_bytes():
    result = mc_distribution_histogram(SAMPLE_MC)
    assert isinstance(result, bytes)
    assert result[:4] == b'\x89PNG'


def test_kill_vector_bar_returns_png_bytes():
    result = kill_vector_bar(SAMPLE_MC)
    assert isinstance(result, bytes)


def test_tornado_chart_returns_png_bytes():
    sensitivity = [{"param": "churn_rate", "low_delta": -0.1, "high_delta": 0.05}]
    result = tornado_chart(sensitivity)
    assert isinstance(result, bytes)


def test_cohort_gauge_returns_png_bytes():
    result = cohort_percentile_gauge(72.0, 64.0)
    assert isinstance(result, bytes)


def test_charts_are_deterministic():
    r1 = cash_flow_curve(SAMPLE_TICKS)
    r2 = cash_flow_curve(SAMPLE_TICKS)
    assert r1 == r2


def test_render_charts_for_run_creates_files(tmp_path):
    bundle = render_charts_for_run(SAMPLE_TICKS, SAMPLE_MC, "run_001", str(tmp_path))
    assert (tmp_path / "cash_flow.png").exists()
    assert (tmp_path / "mc_histogram.png").exists()
    assert (tmp_path / "kill_vectors.png").exists()
    assert (tmp_path / "resilience_gauge.png").exists()


def test_chart_bundle_get_path(tmp_path):
    bundle = render_charts_for_run(SAMPLE_TICKS, SAMPLE_MC, "run_001", str(tmp_path))
    path = bundle.get_path("cash_flow")
    assert path is not None
    assert path.exists()
    assert path.stat().st_size > 1000  # PNG has real content


def test_empty_mc_does_not_crash():
    result = kill_vector_bar({})
    assert isinstance(result, bytes)
```

---

## Verification Commands

```bash
cd backend && pip install matplotlib==3.9.0 seaborn==0.13.2
cd backend && pytest tests/unit/deep_report/test_charts.py -v
cd backend && ruff check app/utils/charts.py app/services/deep_report/chart_builder.py
```
