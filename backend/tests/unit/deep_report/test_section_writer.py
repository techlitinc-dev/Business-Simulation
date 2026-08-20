"""Unit tests for the deep-report section writer (Day 03)."""

from __future__ import annotations

import json
from typing import Any

from app.agents.llm.base import MockProvider
from app.agents.section_writer import (
    _get_schema,
    _load_prompt,
    generate_section,
    render_data_only_fallback,
)
from app.services.deep_report.manifest import DataInputKey, SectionDef
from app.services.deep_report.section_schemas import ExecutiveSummarySection


def _sec(*, template: str = "executive_summary.md") -> SectionDef:
    return SectionDef(
        section_number=2,
        title="Executive Summary",
        page_budget=2,
        data_inputs=[DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES],
        prompt_template=template,
    )


def _pack() -> dict[str, Any]:
    return {
        "tick_logs": [{"month": 1, "revenue": 5000, "cash": 12000}],
        "mc_aggregates": {"survival_rate": 0.75, "n_runs": 20},
    }


async def test_generate_section_returns_dict_with_narrative() -> None:
    provider = MockProvider()
    canned = json.dumps(
        {
            "verdict": "PASS",
            "headline_metrics": ["Revenue 5000", "Cash 12000", "Survival 75%"],
            "narrative": "The simulation survived with healthy cash. " * 8,
            "risk_level": "MEDIUM",
        }
    )
    provider.register("Generate section", canned)

    result = await generate_section(_sec(), _pack(), provider=provider)
    assert isinstance(result, dict)
    assert "narrative" in result
    assert result["section_number"] == 2
    assert result["title"] == "Executive Summary"
    assert result["verdict"] == "PASS"
    assert result.get("is_fallback") is None


async def test_generate_section_falls_back_when_provider_invalid() -> None:
    # Unregistered MockProvider returns "{}" -> StructuredOutputError -> fallback.
    provider = MockProvider()
    result = await generate_section(_sec(), _pack(), provider=provider)
    assert result["is_fallback"] is True
    assert result["section_number"] == 2
    assert "AI narrative unavailable" in result["narrative"]


def test_data_only_fallback_never_raises() -> None:
    # Covers every manifest section template/data combination shape.
    from app.services.deep_report.registry import FULL_MANIFEST

    for section in FULL_MANIFEST.sections:
        pack = {k.value: None for k in section.data_inputs}
        out = render_data_only_fallback(section, pack)
        assert out["section_number"] == section.section_number
        assert out["title"] == section.title
        assert "narrative" in out
        assert out["is_fallback"] is True

    # Non-None data values render too.
    section = _sec()
    out = render_data_only_fallback(section, _pack())
    assert "Tick Logs" in out["narrative"]
    assert "survival_rate" in out["narrative"]


def test_load_prompt_uses_generic_when_missing() -> None:
    section = _sec(template="nonexistent.md")
    prompt = _load_prompt(section.prompt_template, section, _pack())
    assert "section 2" in prompt or "2" in prompt
    assert '"survival_rate": 0.75' in prompt


def test_schema_map_defaults_to_generic() -> None:
    from app.services.deep_report.section_schemas import GenericNarrativeSection

    assert _get_schema("executive_summary.md") is ExecutiveSummarySection
    assert _get_schema("unknown.md") is GenericNarrativeSection
