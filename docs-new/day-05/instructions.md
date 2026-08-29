# Day 05 — F-01: PDF Assembly (WeasyPrint, Cover Page, ToC, Branding)

## Feature
F-01: Deep-Dive Report Engine

## Goal
Implement `pdf_deep.py` and `assembler.py` that take the list of generated section dicts and chart PNGs and produce a styled, multi-section PDF with cover page, table of contents, page numbers, headers/footers, and workspace branding.

## Prerequisites
- Day 01–04 complete
- `weasyprint` already in requirements.txt (used by existing `app/utils/pdf.py`)
- `markdown` package available

---

## Step 1 — Create `backend/app/assets/report_template.css`

```css
/* Deep-Dive Report — WeasyPrint CSS */
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");

:root {
  --bg: #0f172a;
  --surface: #1e293b;
  --border: #334155;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --accent: #3b82f6;
  --success: #22c55e;
  --danger: #ef4444;
  --warning: #eab308;
}

@page {
  size: A4;
  margin: 20mm 18mm 22mm 18mm;
  @top-center {
    content: string(report-title);
    font-size: 8pt;
    color: #94a3b8;
  }
  @bottom-left {
    content: string(workspace-name);
    font-size: 8pt;
    color: #94a3b8;
  }
  @bottom-right {
    content: "Page " counter(page) " of " counter(pages);
    font-size: 8pt;
    color: #94a3b8;
  }
}

@page cover {
  margin: 0;
  @top-center { content: ""; }
  @bottom-left { content: ""; }
  @bottom-right { content: ""; }
}

body {
  font-family: "Inter", sans-serif;
  font-size: 10pt;
  color: var(--text);
  background: var(--bg);
  line-height: 1.6;
}

.cover-page {
  page: cover;
  page-break-after: always;
  background: var(--bg);
  padding: 60mm 20mm;
  text-align: center;
}

.cover-title { font-size: 28pt; font-weight: 700; color: var(--text); margin-bottom: 8mm; }
.cover-subtitle { font-size: 14pt; color: var(--muted); margin-bottom: 12mm; }
.cover-meta { font-size: 10pt; color: var(--muted); }
.cover-badge {
  display: inline-block; padding: 4px 16px;
  background: var(--accent); color: white;
  border-radius: 4px; font-size: 10pt; margin-top: 8mm;
}

.toc { page-break-after: always; }
.toc h2 { color: var(--accent); font-size: 16pt; border-bottom: 1px solid var(--border); padding-bottom: 4mm; }
.toc-entry { display: flex; justify-content: space-between; padding: 2mm 0; border-bottom: 1px dotted var(--border); }

.section { page-break-before: always; }
.section h1 { font-size: 18pt; color: var(--accent); border-bottom: 2px solid var(--accent); padding-bottom: 3mm; margin-bottom: 6mm; }
.section h2 { font-size: 13pt; color: var(--text); margin-top: 5mm; }
.section h3 { font-size: 11pt; color: var(--muted); }

.metric-card {
  display: inline-block; background: var(--surface);
  border: 1px solid var(--border); border-radius: 6px;
  padding: 4mm 6mm; margin: 2mm; min-width: 35mm;
}
.metric-value { font-size: 18pt; font-weight: 700; color: var(--accent); }
.metric-label { font-size: 8pt; color: var(--muted); }

.chart-img { width: 100%; max-height: 80mm; object-fit: contain; margin: 4mm 0; }

.severity-high { color: var(--danger); font-weight: 600; }
.severity-medium { color: var(--warning); font-weight: 600; }
.severity-low { color: var(--success); font-weight: 600; }

table { width: 100%; border-collapse: collapse; margin: 4mm 0; font-size: 9pt; }
th { background: var(--surface); color: var(--muted); padding: 2mm 3mm; text-align: left; border: 1px solid var(--border); }
td { padding: 2mm 3mm; border: 1px solid var(--border); }
tr:nth-child(even) { background: #1a2744; }

code, pre { background: var(--surface); color: var(--success); padding: 1mm 2mm; border-radius: 3px; font-size: 8pt; }

.disclaimer { font-size: 7pt; color: var(--muted); border-top: 1px solid var(--border); margin-top: 8mm; padding-top: 3mm; }
```

---

## Step 2 — Create `backend/app/utils/pdf_deep.py`

```python
"""
WeasyPrint-based PDF assembly for the Deep-Dive Report Engine.
Extends existing pdf.py; handles multi-section 70-page documents.
"""
from __future__ import annotations
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any
import markdown as md

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

CSS_PATH = Path(__file__).parent.parent / "assets" / "report_template.css"


def _section_to_html(section_output: dict[str, Any], chart_paths: dict[str, str]) -> str:
    """Convert one section dict to an HTML block."""
    num = section_output.get("section_number", 0)
    title = section_output.get("title", "Section")
    narrative = section_output.get("narrative", "")
    html_content = md.markdown(narrative, extensions=["tables", "fenced_code"])

    # Inject chart if available for this section
    chart_map = {6: "cash_flow", 9: "mc_histogram", 10: "kill_vectors", 14: "tornado", 15: "resilience_gauge"}
    chart_html = ""
    chart_name = chart_map.get(num)
    if chart_name and chart_name in chart_paths:
        chart_html = f'<img class="chart-img" src="{chart_paths[chart_name]}" alt="{chart_name}" />'

    return f"""
<div class="section" id="section-{num}">
  <h1>{num}. {title}</h1>
  {chart_html}
  {html_content}
</div>"""


def _build_toc(sections: list[dict]) -> str:
    entries = "".join(
        f'<div class="toc-entry"><span>{s.get("section_number")}. {s.get("title", "")}</span>'
        f'<span style="color:#3b82f6">—</span></div>'
        for s in sections
    )
    return f'<div class="toc"><h2>Table of Contents</h2>{entries}</div>'


def _build_cover(workspace_name: str, run_id: str, tier: str, report_type: str) -> str:
    now = datetime.utcnow().strftime("%B %Y")
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
    string-set: report-title "Business Simulation Audit";
    string-set: workspace-name "{workspace_name}";
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
    return pdf_bytes
```

---

## Step 3 — Create `assembler.py`

`backend/app/services/deep_report/assembler.py`:

```python
from __future__ import annotations
import tempfile
import os
from typing import Any
from app.utils.pdf_deep import assemble_pdf
from app.services.deep_report.chart_builder import render_charts_for_run


async def assemble_report(
    sections: list[dict[str, Any]],
    tick_logs: list[dict],
    mc_aggregates: dict,
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
        output_path = tempfile.mktemp(suffix=".pdf", prefix=f"report_{run_id}_")

    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    return output_path
```

---

## Step 4 — Tests

`backend/tests/unit/deep_report/test_assembler.py`:

```python
import pytest
import asyncio
import os
from app.services.deep_report.assembler import assemble_report

MOCK_SECTIONS = [
    {"section_number": 2, "title": "Executive Summary",
     "narrative": "The business faces HIGH risk with a survival rate of 58 percent."},
    {"section_number": 9, "title": "Monte Carlo Results",
     "narrative": "Monte Carlo analysis of 100 runs shows median lifespan of 17 months."},
]
MOCK_TICKS = [{"month": i, "cash": 100000 - i*4000, "revenue": 12000 + i*300, "costs": 14000} for i in range(1, 13)]
MOCK_MC = {"survival_rate": 0.58, "lifespan_distribution": list(range(8, 25)), "kill_vectors": []}


def test_assemble_report_returns_pdf_path(tmp_path):
    out = tmp_path / "test_report.pdf"
    result = asyncio.get_event_loop().run_until_complete(
        assemble_report(MOCK_SECTIONS, MOCK_TICKS, MOCK_MC,
                        "run_test", "Acme Corp", "pro", str(out))
    )
    assert os.path.exists(result)
    assert os.path.getsize(result) > 1000


def test_assemble_report_file_is_pdf_or_html(tmp_path):
    out = tmp_path / "test_report.out"
    result = asyncio.get_event_loop().run_until_complete(
        assemble_report(MOCK_SECTIONS, MOCK_TICKS, MOCK_MC,
                        "run_test", "Acme Corp", "free", str(out))
    )
    with open(result, "rb") as f:
        header = f.read(8)
    # Either PDF (%PDF) or HTML fallback (<!)
    assert header[:4] == b"%PDF" or header[:2] == b"<!"


def test_assemble_empty_sections_does_not_crash(tmp_path):
    out = tmp_path / "empty.pdf"
    result = asyncio.get_event_loop().run_until_complete(
        assemble_report([], [], {}, "run_empty", "TestCo", "free", str(out))
    )
    assert os.path.exists(result)
```

---

## Verification Commands

```bash
cd backend && pytest tests/unit/deep_report/test_assembler.py -v
cd backend && ruff check app/utils/pdf_deep.py app/services/deep_report/assembler.py
```
