"""Day 01 tests: deep-report manifest, registry, data pack, and Celery task."""

import pytest
from app.db.session import async_session_factory
from app.services.deep_report.data_pack import build_data_pack
from app.services.deep_report.manifest import (
    DataInputKey,
    ReportManifest,
    ReportTier,
    SectionDef,
)
from app.services.deep_report.registry import FULL_MANIFEST, get_manifest
from pydantic import ValidationError


def test_full_manifest_section_count() -> None:
    assert len(FULL_MANIFEST.sections) == 21


def test_full_manifest_total_pages() -> None:
    assert FULL_MANIFEST.total_page_budget == 70


def test_free_tier_sections() -> None:
    sections = FULL_MANIFEST.sections_for_tier(ReportTier.FREE)
    assert len(sections) == 3
    assert {s.section_number for s in sections} == {2, 9, 11}


def test_pro_tier_sections() -> None:
    sections = FULL_MANIFEST.sections_for_tier(ReportTier.PRO)
    numbers = {s.section_number for s in sections}
    assert numbers.issuperset({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13})
    assert 14 not in numbers
    assert 21 not in numbers


def test_enterprise_tier_all_sections() -> None:
    sections = FULL_MANIFEST.sections_for_tier(ReportTier.ENTERPRISE)
    assert len(sections) == 21


def test_section_def_invalid_section_number() -> None:
    with pytest.raises(ValidationError):
        SectionDef(
            section_number=0,
            title="x",
            page_budget=2,
            data_inputs=[],
            prompt_template="x.md",
        )


def test_section_def_invalid_title_too_short() -> None:
    with pytest.raises(ValidationError):
        SectionDef(
            section_number=1,
            title="x",
            page_budget=2,
            data_inputs=[],
            prompt_template="x.md",
        )


def test_get_manifest_known_type() -> None:
    manifest = get_manifest("resilience_audit")
    assert isinstance(manifest, ReportManifest)


def test_get_manifest_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_manifest("nonexistent")


def test_manifest_page_budget_auto_computed() -> None:
    manifest = ReportManifest(
        name="Test",
        report_type="resilience_audit",
        tier=ReportTier.FREE,
        sections=[
            SectionDef(
                section_number=1,
                title="Sec One",
                page_budget=3,
                data_inputs=[DataInputKey.RUN_METADATA],
                prompt_template="x.md",
            ),
            SectionDef(
                section_number=2,
                title="Sec Two",
                page_budget=5,
                data_inputs=[DataInputKey.BLUEPRINT],
                prompt_template="y.md",
            ),
        ],
    )
    assert manifest.total_page_budget == 8


async def test_data_pack_returns_all_requested_keys() -> None:
    """The data pack always includes every requested key (never fabricates).

    Against an empty DB a missing run yields no ticks ([]) and no MC
    aggregates (None) — the keys are present regardless.
    """
    section = SectionDef(
        section_number=2,
        title="Executive Summary",
        page_budget=2,
        data_inputs=[DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES],
        prompt_template="executive_summary.md",
    )
    async with async_session_factory() as db:
        result = await build_data_pack(section, "run_test_123", db)

    assert "tick_logs" in result
    assert "mc_aggregates" in result
    assert result["tick_logs"] == []
    assert result["mc_aggregates"] is None


def test_celery_task_importable() -> None:
    from app.workers.report_job import generate_deep_report

    assert generate_deep_report.name == "forge.generate_deep_report"
