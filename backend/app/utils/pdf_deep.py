"""
WeasyPrint-based PDF assembly for the Deep-Dive Report Engine.
Extends existing pdf.py; handles multi-section 70-page documents.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import markdown as md

try:
    from weasyprint import CSS, HTML

    WEASYPRINT_AVAILABLE = True
except ImportError:  # pragma: no cover - env-specific
    WEASYPRINT_AVAILABLE = False

CSS_PATH = Path(__file__).parent.parent / "assets" / "report_template.css"


def _section_to_html(
    section_output: dict[str, Any], chart_paths: dict[str, str]
) -> str:
    """Convert one section dict to an HTML block."""
    num = section_output.get("section_number", 0)
    title = section_output.get("title", "Section")
    narrative = section_output.get("narrative", "")
    html_content = md.markdown(narrative, extensions=["tables", "fenced_code"])

    # Inject chart if available for this section
    chart_map = {
        6: "cash_flow",
        9: "mc_histogram",
        10: "kill_vectors",
        14: "tornado",
        15: "resilience_gauge",
    }
    chart_html = ""
    chart_name = chart_map.get(num)
    if chart_name and chart_name in chart_paths:
        chart_html = (
            f'<img class="chart-img" src="{chart_paths[chart_name]}" '
            f'alt="{chart_name}" />'
        )

    return f"""
<div class="section" id="section-{num}">
  <h1>{num}. {title}</h1>
  {chart_html}
  {html_content}
</div>"""


def _build_toc(sections: list[dict[str, Any]]) -> str:
    entries = "".join(
        f'<div class="toc-entry"><span>{s.get("section_number")}. {s.get("title", "")}</span>'
        f'<span style="color:#3b82f6">—</span></div>'
        for s in sections
    )
    return f'<div class="toc"><h2>Table of Contents</h2>{entries}</div>'


def _build_cover(
    workspace_name: str, run_id: str, tier: str, report_type: str
) -> str:
    now = datetime.now(UTC).strftime("%B %Y")
    tier_label = tier.upper()
    return f"""
<div class="cover-page">
  <div class="cover-title">Business Simulation<br/>Resilience Audit</div>
  <div class="cover-subtitle">{report_type.replace("_", " ").title()}</div>
  <div class="cover-meta">
    Workspace: <strong>{workspace_name}</strong><br/>
    Run ID: {run_id}<br/>
    Generated: {now}
  </div>
  <div class="cover-badge">{tier_label} REPORT</div>
  <div class="disclaimer">
    This report is generated from deterministic simulation data. All financial figures are
    simulated projections and do not constitute financial advice. AI-generated narrative
    sections are grounded in engine data but should be reviewed by a qualified professional.
  </div>
</div>"""


def assemble_pdf(
    sections: list[dict[str, Any]],
    chart_paths: dict[str, str],
    workspace_name: str,
    run_id: str,
    tier: str,
    report_type: str = "resilience_audit",
) -> bytes:
    """
    Assemble all sections + charts into a styled PDF.
    Returns PDF as bytes.
    Falls back to minimal HTML→PDF if WeasyPrint is unavailable.
    """
    cover_html = _build_cover(workspace_name, run_id, tier, report_type)
    toc_html = _build_toc(sections)
    sections_html = "\n".join(_section_to_html(s, chart_paths) for s in sections)

    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    @page {{
      string-set: report-title "Business Simulation Audit";
      string-set: workspace-name "{workspace_name}";
    }}
  </style>
</head>
<body>
  {cover_html}
  {toc_html}
  {sections_html}
</body>
</html>"""

    if not WEASYPRINT_AVAILABLE:
        # Minimal fallback for environments without WeasyPrint
        return full_html.encode("utf-8")

    css = CSS(filename=str(CSS_PATH)) if CSS_PATH.exists() else None
    pdf_bytes = HTML(string=full_html).write_pdf(stylesheets=[css] if css else [])
    return bytes(pdf_bytes)
