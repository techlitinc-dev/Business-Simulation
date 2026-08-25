"""Unit tests for the investor tools agent (Day 22)."""

from __future__ import annotations

from app.agents.investor_tools import (
    generate_pitch_outline,
    generate_teaser,
    pitch_outline_to_pdf,
    teaser_to_pdf,
)
from app.core.config import get_settings
from app.schemas.investor import InvestmentTeaser, PitchDeckOutline, PitchSlide

MOCK_DATA = {
    "mc_aggregates": {"survival_rate": 0.68, "median_lifespan": 18},
    "tick_logs": [{"month": 1, "revenue": 12000, "cash": 86000}],
    "forge_vulnerabilities": [{"title": "High CAC", "severity": "HIGH"}],
}


def _force_mock() -> None:
    settings = get_settings()
    settings.llm_provider = "mock"
    settings.llm_api_key = ""


async def test_generate_teaser_returns_teaser() -> None:
    _force_mock()
    result = await generate_teaser(MOCK_DATA)
    assert result.problem
    assert result.simulated_survival
    assert len(result.key_metrics) >= 3


async def test_generate_pitch_outline_has_10_plus_slides() -> None:
    _force_mock()
    result = await generate_pitch_outline(MOCK_DATA)
    assert len(result.slides) >= 10


def test_teaser_to_pdf_returns_bytes() -> None:
    teaser = InvestmentTeaser(
        problem="Test problem.",
        solution="Test solution.",
        simulated_survival="68% survival",
        key_metrics=["MRR: $12k", "CAC: $450", "Runway: 18mo"],
        ask="Raising $500K",
        risks=["High churn"],
    )
    pdf = teaser_to_pdf(teaser, "TestCo", "run_001")
    assert isinstance(pdf, bytes)
    assert len(pdf) > 100


async def test_teaser_survival_grounded_in_mc_data() -> None:
    _force_mock()
    result = await generate_teaser(MOCK_DATA)
    survival_pct = int(round(MOCK_DATA["mc_aggregates"]["survival_rate"] * 100))
    assert str(survival_pct) in result.simulated_survival


def test_pitch_outline_to_pdf_returns_bytes() -> None:
    outline = PitchDeckOutline(
        slides=[
            PitchSlide(
                slide_number=i + 1,
                title=f"Slide {i + 1}",
                talking_points=[f"Key point for slide {i + 1}."],
            )
            for i in range(11)
        ]
    )
    pdf = pitch_outline_to_pdf(outline, "TestCo", "run_001")
    assert isinstance(pdf, bytes)
    assert len(pdf) > 100
