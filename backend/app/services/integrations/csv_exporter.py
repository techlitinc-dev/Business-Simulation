"""CSV export helpers — tick logs and Monte Carlo aggregates."""

from __future__ import annotations

import csv
import io
from typing import Any


def ticks_to_csv(tick_logs: list[dict[str, Any]]) -> str:
    """Serialize tick logs to CSV (header + one row per tick)."""
    buf = io.StringIO()
    if not tick_logs:
        return "month\n"
    writer = csv.DictWriter(buf, fieldnames=list(tick_logs[0].keys()))
    writer.writeheader()
    writer.writerows(tick_logs)
    return buf.getvalue()


def mc_to_csv(mc_aggregates: dict[str, Any]) -> str:
    """Serialize Monte Carlo aggregates to CSV.

    Scalars become ``metric,value`` rows; ``kill_vectors`` (a dict of
    kill-vector type -> count) become a second block.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["metric", "value"])
    for key, value in mc_aggregates.items():
        if key == "kill_vectors":
            continue
        if not isinstance(value, (list, dict)):
            writer.writerow([key, value])
    kill_vectors = mc_aggregates.get("kill_vectors")
    if isinstance(kill_vectors, dict):
        writer.writerow([])
        writer.writerow(["kill_vector_type", "frequency"])
        for kv_type, frequency in kill_vectors.items():
            writer.writerow([kv_type, frequency])
    return buf.getvalue()
