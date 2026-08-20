from __future__ import annotations

import os
import tempfile
from typing import Any

from app.services.deep_report.chart_builder import render_charts_for_run
from app.utils.pdf_deep import assemble_pdf


async def assemble_report(
    sections: list[dict[str, Any]],
    tick_logs: list[dict[str, Any]],
    mc_aggregates: dict[str, Any],
    run_id: str,
    workspace_name: str,
    tier: str,
    output_path: str | None = None,
) -> str:
    """
    Render charts, assemble sections, produce PDF.
    Returns the filesystem path to the final PDF.
    """
    with tempfile.TemporaryDirectory() as chart_dir:
        bundle = render_charts_for_run(tick_logs, mc_aggregates, run_id, chart_dir)
        chart_paths = {name: str(path) for name, path in bundle.charts.items()}

        pdf_bytes = assemble_pdf(
            sections=sections,
            chart_paths=chart_paths,
            workspace_name=workspace_name,
            run_id=run_id,
            tier=tier,
        )

    if output_path is None:
        fd, output_path = tempfile.mkstemp(
            suffix=".pdf", prefix=f"report_{run_id}_"
        )
        os.close(fd)

    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    return output_path
