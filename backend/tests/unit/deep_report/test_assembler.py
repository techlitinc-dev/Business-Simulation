"""Day 05 tests: deep-report PDF assembler (app.services.deep_report.assembler).

Covers end-to-end assembly (sections + charts → PDF file) plus the
cover / ToC / section-HTML builders that feed the PDF.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.deep_report.assembler import assemble_report
from app.utils.pdf_deep import _build_cover, _build_toc, _section_to_html

CHART_PATHS: dict[str, str] = {"cash_flow": "/tmp/charts/cash_flow.png"}


def _ticks() -> list[dict[str, Any]]:
    return [
        {"month": m, "cash_balance": 100000 - m * 3000, "revenue": m * 5000, "costs": 60000}
        for m in range(1, 25)
    ]


def _mc() -> dict[str, Any]:
    return {
        "survival_rate": 0.62,
        "n_runs": 100,
        "kill_vectors": {"financial": 22, "market": 10},
        "runs_summary": [
            {"seed": i, "survived": True, "lifespan_months": 20} for i in range(100)
        ],
    }


def _sections() -> list[dict[str, Any]]:
    return [
        {
            "section_number": 6,
            "title": "24-Month Financial Narrative",
            "narrative": "Cash declined steadily while revenue grew.",
        },
        {
            "section_number": 9,
            "title": "Monte Carlo Results",
            "narrative": "62% of runs survived 24 months.",
        },
    ]


async def test_assemble_report_returns_pdf_path(tmp_path: Path) -> None:
    """assemble_report returns a path to a file that exists and is >1KB."""
    out = str(tmp_path / "report.pdf")
    path = await assemble_report(
        _sections(), _ticks(), _mc(), "run_1", "Demo Ventures", "pro", output_path=out
    )
    assert path == out
    assert Path(path).exists()
    assert Path(path).stat().st_size > 1024


async def test_assemble_report_file_is_pdf_or_html(tmp_path: Path) -> None:
    """File starts with %PDF or <! (HTML fallback when WeasyPrint missing)."""
    out = str(tmp_path / "test_report.out")
    path = await assemble_report(_sections(), _ticks(), _mc(), "run_3", "Acme", "free", out)
    header = Path(path).read_bytes()[:8]
    assert header[:4] == b"%PDF" or header[:2] == b"<!"


async def test_assemble_empty_sections_does_not_crash(tmp_path: Path) -> None:
    """Empty sections + empty ticks + empty mc → file still created."""
    out = str(tmp_path / "empty.pdf")
    path = await assemble_report([], [], {}, "run_empty", "TestCo", "free", out)
    assert Path(path).exists()
    assert Path(path).stat().st_size > 0


def test_section_to_html_includes_title() -> None:
    """_section_to_html output contains the section title."""
    html = _section_to_html(_sections()[0], CHART_PATHS)
    assert "24-Month Financial Narrative" in html


def test_cover_contains_workspace_name() -> None:
    """_build_cover output contains the workspace name."""
    cover = _build_cover("Acme Corp", "run_001", "pro", "resilience_audit")
    assert "Acme Corp" in cover


def test_toc_has_all_section_titles() -> None:
    """_build_toc output contains every section title."""
    toc = _build_toc(_sections())
    assert "24-Month Financial Narrative" in toc
    assert "Monte Carlo Results" in toc


def test_chart_injected_for_section_6() -> None:
    """cash_flow chart path is injected for section 6."""
    html = _section_to_html(_sections()[0], CHART_PATHS)  # section 6 → cash_flow
    assert 'class="chart-img"' in html
    assert "cash_flow.png" in html
