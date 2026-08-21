"""Certification PDF generation — 'Forge-Validated Business' certificate."""

from __future__ import annotations

from typing import Any

from app.utils.pdf_deep import assemble_pdf


def generate_certification(
    workspace_name: str, score: float, percentile: float, run_id: str
) -> bytes:
    """Build a 'Forge-Validated Business' certification PDF."""
    content = f"""# Forge-Validated Business Certificate

**{workspace_name}** has completed a rigorous AI-powered business simulation audit.

## Resilience Score: {score:.1f} / 100

This places the business in the **{percentile:.0f}th percentile** of all simulated businesses.

## Certification Criteria Met
- ✅ 24-month deterministic simulation completed
- ✅ Monte Carlo stress-test across 100+ scenarios
- ✅ AI vulnerability analysis reviewed
- ✅ Optimization recommendations evaluated

*Run ID: {run_id} · Certified by The Forge Simulation Engine*
"""
    section: dict[str, Any] = {
        "section_number": 1,
        "title": "Certification",
        "narrative": content,
    }
    return assemble_pdf(
        sections=[section],
        chart_paths={},
        workspace_name=workspace_name,
        run_id=run_id,
        tier="enterprise",
        report_type="resilience_audit",
    )
