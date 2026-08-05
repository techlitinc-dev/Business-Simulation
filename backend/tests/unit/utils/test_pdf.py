"""Unit tests for PDF rendering (T32)."""

from app.utils.pdf import render_report_pdf


def test_pdf_bytes_start_with_magic() -> None:
    pdf = render_report_pdf(
        "### SURVIVAL METRICS\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n",
        title="The Forge — Resilience Audit",
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_pdf_empty_markdown_still_renders() -> None:
    pdf = render_report_pdf("", title="Empty")
    assert pdf.startswith(b"%PDF")
