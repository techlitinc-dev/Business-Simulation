import pytest
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
    numbers = [s.section_number for s in sections]
    assert 2 in numbers  # executive summary
    assert 9 in numbers  # monte carlo
    assert 11 in numbers  # weaknesses
    assert len(sections) == 3


def test_pro_tier_sections() -> None:
    sections = FULL_MANIFEST.sections_for_tier(ReportTier.PRO)
    numbers = [s.section_number for s in sections]
    assert 1 in numbers
    assert 13 in numbers
    assert 14 not in numbers  # enterprise only


def test_enterprise_tier_all_sections() -> None:
    sections = FULL_MANIFEST.sections_for_tier(ReportTier.ENTERPRISE)
    assert len(sections) == 21


def test_section_def_validation() -> None:
    with pytest.raises(ValidationError):
        SectionDef(
            section_number=0,  # invalid: ge=1
            title="x",
            page_budget=2,
            data_inputs=[],
            prompt_template="x.md",
        )


def test_get_manifest_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_manifest("nonexistent_type")


def test_manifest_page_budget_computed() -> None:
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
