"""Unit tests for the deep-report PDF assembler (Day 05)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.utils import pdf_deep
from app.utils.pdf_deep import (
    _build_cover,
    _build_toc,
    _section_to_html,
    assemble_pdf,
)

_SECTIONS: list[dict[str, Any]] = [
    {
        "section_number": 6,
        "title": "24-Month Financial Narrative",
        "narrative": "Revenue grew steadily to **5,000** by month 12.",
    },
    {
        "section_number": 9,
        "title": "Monte Carlo Results",
        "narrative": "| Metric | Value |\n| --- | --- |\n| Survival | 62% |",
    },
]


def test_assemble_pdf_returns_pdf_bytes(tmp_path: Path) -> None:
    chart_paths = {"cash_flow": str(tmp_path / "cash_flow.png")}
    (tmp_path / "cash_flow.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)

    pdf = assemble_pdf(_SECTIONS, chart_paths, "Demo", "run_1", "pro")
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_assemble_pdf_html_fallback_when_no_weasyprint(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(pdf_deep, "WEASYPRINT_AVAILABLE", False)
    pdf = assemble_pdf(_SECTIONS, {}, "Demo", "run_1", "free")
    assert pdf.startswith(b"<!DOCTYPE")
    assert b"Table of Contents" in pdf


def test_build_cover_includes_tier_and_workspace() -> None:
    html = _build_cover("Demo Ventures", "run_9", "enterprise", "resilience_audit")
    assert "ENTERPRISE REPORT" in html
    assert "Demo Ventures" in html
    assert "run_9" in html


def test_build_toc_has_one_entry_per_section() -> None:
    html = _build_toc(_SECTIONS)
    assert html.count("toc-entry") == 2
    assert "24-Month Financial Narrative" in html


def test_section_to_html_injects_chart_for_known_section(tmp_path: Path) -> None:
    chart_paths = {"cash_flow": str(tmp_path / "cash_flow.png")}
    html = _section_to_html(_SECTIONS[0], chart_paths)  # section 6 -> cash_flow
    assert 'class="chart-img"' in html
    assert "cash_flow.png" in html


def test_section_to_html_renders_markdown() -> None:
    html = _section_to_html(_SECTIONS[0], {})
    assert "<strong>5,000</strong>" in html
    assert "<table>" in _section_to_html(_SECTIONS[1], {})
