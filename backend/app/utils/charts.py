"""
Server-side chart rendering for the Deep-Dive Report Engine.
All charts are deterministic (same data → same PNG bytes).
No LLM involvement.
"""
from __future__ import annotations

import hashlib
import io
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless, no display required

import matplotlib.pyplot as plt  # noqa: E402 - after matplotlib.use("Agg")
import numpy as np  # noqa: E402

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


def _apply_style() -> None:
    plt.rcParams.update(CHART_STYLE)


def _save_to_bytes(fig: Any) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def cash_flow_curve(tick_logs: list[dict[str, Any]]) -> bytes:
    """Line chart: cash, revenue, costs over time."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(10, 4))
    months = [t["month"] for t in tick_logs]
    # The data pack flattens TickLog.kpis, whose canonical key is cash_balance.
    ax.plot(
        months, [t.get("cash_balance", t.get("cash", 0)) for t in tick_logs],
        label="Cash", color="#3b82f6", linewidth=2,
    )
    ax.plot(months, [t.get("revenue", 0) for t in tick_logs], label="Revenue",
            color="#22c55e", linewidth=1.5)
    ax.plot(months, [t.get("costs", 0) for t in tick_logs], label="Costs",
            color="#ef4444", linewidth=1.5, linestyle="--")
    ax.axhline(0, color="#f59e0b", linewidth=0.8, linestyle=":")
    ax.set_xlabel("Month")
    ax.set_ylabel("Amount ($)")
    ax.set_title("Cash Flow Over 24 Months")
    ax.legend(facecolor="#1e293b", edgecolor="#334155")
    ax.grid(True, alpha=0.3)
    return _save_to_bytes(fig)


def mc_distribution_histogram(mc_aggregates: dict[str, Any]) -> bytes:
    """Histogram of survival outcomes from Monte Carlo runs."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(8, 4))
    lifespan_dist = mc_aggregates.get("lifespan_distribution", [])
    if not lifespan_dist:
        # Real MC results store per-run lifespans in runs_summary.
        lifespan_dist = [
            r.get("lifespan_months", 0)
            for r in mc_aggregates.get("runs_summary", [])
        ]
    if not lifespan_dist:
        lifespan_dist = list(range(1, 25))  # placeholder
    ax.hist(lifespan_dist, bins=24, color="#6366f1", edgecolor="#4338ca", alpha=0.85)
    survival_rate = mc_aggregates.get("survival_rate", 0)
    ax.set_title(f"Simulated Business Lifespan Distribution (Survival: {survival_rate:.0%})")
    ax.set_xlabel("Months Survived")
    ax.set_ylabel("Number of Runs")
    ax.grid(True, alpha=0.3)
    return _save_to_bytes(fig)


def kill_vector_bar(mc_aggregates: dict[str, Any]) -> bytes:
    """Horizontal bar chart of top failure causes."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(8, 4))
    kill_vectors = mc_aggregates.get("kill_vectors", [])
    if not kill_vectors:
        kill_vectors = [{"type": "No data", "frequency": 1.0}]

    # Real MC results store kill_vectors as {cause: count}; a list of
    # {"type", "frequency"} dicts is also accepted.
    if isinstance(kill_vectors, dict):
        total = sum(kill_vectors.values()) or 1
        items = sorted(kill_vectors.items(), key=lambda kv: -kv[1])
        labels = [k.replace("_", " ").title() for k, _ in items]
        values = [c / total * 100 for _, c in items]
    else:
        labels = [kv.get("type", "unknown").replace("_", " ").title() for kv in kill_vectors]
        values = [kv.get("frequency", 0) * 100 for kv in kill_vectors]

    colors = ["#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e"]
    ax.barh(labels, values, color=colors[: len(labels)])
    ax.set_xlabel("% of Failed Runs")
    ax.set_title("Top Kill Vectors")
    ax.grid(True, axis="x", alpha=0.3)
    return _save_to_bytes(fig)


def tornado_chart(sensitivity_results: list[dict[str, Any]]) -> bytes:
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
    ax.barh(
        y,
        [abs(delta) for delta in low_deltas],
        left=[min(delta, 0) for delta in low_deltas],
        color="#ef4444", alpha=0.8, label="Negative impact",
    )
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
    ax.text(0, 0, f"{score:.0f}", ha="center", va="center", fontsize=28,
            color=color, fontweight="bold")
    ax.set_title(f"Resilience Score — {percentile:.0f}th Percentile vs. Peers", pad=15)
    return _save_to_bytes(fig)


def chart_sha256(png_bytes: bytes) -> str:
    """Stable content hash for dedup/caching chart PNGs."""
    return hashlib.sha256(png_bytes).hexdigest()
