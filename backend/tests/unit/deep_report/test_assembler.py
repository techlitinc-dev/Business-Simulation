"""Unit tests for the deep-report PDF assembler service (Day 05)."""

from __future__ import annotations

import glob
import os
import tempfile
from pathlib import Path
from typing import Any

from app.services.deep_report.assembler import assemble_report


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


async def test_assemble_report_writes_pdf_to_output_path(tmp_path: Path) -> None:
    out = str(tmp_path / "report.pdf")
    path = await assemble_report(
        _sections(), _ticks(), _mc(), "run_1", "Demo Ventures", "pro", output_path=out
    )
    assert path == out
    assert Path(path).exists()
    assert Path(path).read_bytes().startswith(b"%PDF")


async def test_assemble_report_without_output_path_returns_temp_file() -> None:
    path = await assemble_report(_sections(), _ticks(), _mc(), "run_2", "Demo", "free")
    assert path.startswith(tempfile.gettempdir())
    assert Path(path).read_bytes().startswith(b"%PDF")
    Path(path).unlink()


async def test_assemble_report_output_is_pdf_or_html(tmp_path: Path) -> None:
    out = str(tmp_path / "test_report.out")
    path = await assemble_report(_sections(), _ticks(), _mc(), "run_3", "Acme", "free", out)
    header = Path(path).read_bytes()[:8]
    assert header[:4] == b"%PDF" or header[:2] == b"<!"
    assert Path(path).stat().st_size > 1000


async def test_assemble_empty_sections_does_not_crash(tmp_path: Path) -> None:
    out = str(tmp_path / "empty.pdf")
    path = await assemble_report([], [], {}, "run_empty", "TestCo", "free", out)
    assert Path(path).exists()
    assert Path(path).stat().st_size > 0


async def test_free_tier_smaller_than_pro(tmp_path: Path) -> None:
    """Fewer sections → fewer pages → smaller file (Day 05 spec item 4)."""
    sections = [
        {
            "section_number": 2,
            "title": "Executive Summary",
            "narrative": "Survival is 68%. " * 30,
        },
        {
            "section_number": 9,
            "title": "Monte Carlo",
            "narrative": "Median lifespan 17 months. " * 20,
        },
    ]
    pro = await assemble_report(
        sections, _ticks(), _mc(), "run_pro", "Acme", "pro",
        output_path=str(tmp_path / "pro.pdf"),
    )
    free = await assemble_report(
        sections[:1], _ticks(), _mc(), "run_free", "TestCo", "free",
        output_path=str(tmp_path / "free.pdf"),
    )
    assert Path(free).stat().st_size < Path(pro).stat().st_size


async def test_no_leftover_temp_chart_dirs(tmp_path: Path) -> None:
    """Temp chart directories are cleaned up after assembly (Day 05 item 6)."""
    out = str(tmp_path / "clean.pdf")
    before = set(glob.glob(os.path.join(tempfile.gettempdir(), "report_charts_*")))
    await assemble_report(_sections(), _ticks(), _mc(), "run_clean", "Acme", "pro", out)
    after = set(glob.glob(os.path.join(tempfile.gettempdir(), "report_charts_*")))
    assert after == before
