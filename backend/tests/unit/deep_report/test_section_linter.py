"""Unit tests for the deep-report section linter (Day 03)."""

from __future__ import annotations

from typing import Any

from app.services.deep_report.manifest import SectionDef
from app.services.deep_report.section_linter import lint_section


def _sec(*, page_budget: int = 2) -> SectionDef:
    return SectionDef(
        section_number=1,
        title="Test Section",
        page_budget=page_budget,
        data_inputs=[],
        prompt_template="test.md",
    )


def _pack() -> dict[str, Any]:
    return {"tick_logs": [{"revenue": 5000, "cash": 12000}]}


def test_lint_passes_on_valid_output() -> None:
    section = _sec()
    narrative = "Revenue reached 5,000 and cash held at 12,000. " * 30
    result = lint_section(section, {"narrative": narrative}, _pack())
    assert result.passed is True
    assert result.errors == []


def test_lint_fails_on_banned_phrase() -> None:
    section = _sec()
    narrative = "As an AI, I cannot provide a full assessment. " * 30
    result = lint_section(section, {"narrative": narrative}, _pack())
    assert result.passed is False
    assert any("as an ai" in e for e in result.errors)


def test_lint_fails_on_short_narrative() -> None:
    section = _sec()
    result = lint_section(section, {"narrative": "Too short."}, _pack())
    assert result.passed is False
    assert any("too short" in e for e in result.errors)


def test_lint_flags_suspicious_number_not_in_data_pack() -> None:
    section = _sec()
    narrative = "The business hit 999999 in revenue. " * 30
    result = lint_section(section, {"narrative": narrative}, _pack())
    assert result.passed is False
    assert any("999999" in e for e in result.errors)


def test_lint_passes_number_present_in_data_pack() -> None:
    section = _sec()
    narrative = "Revenue reached 5,000 this month. " * 50
    result = lint_section(section, {"narrative": narrative}, _pack())
    assert result.passed is True
