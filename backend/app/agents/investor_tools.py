from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.agents import bridge
from app.core.config import get_settings
from app.core.exceptions import StructuredOutputError
from app.schemas.investor import InvestmentTeaser, PitchDeckOutline, PitchSlide
from app.utils.pdf_deep import assemble_pdf

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(template: str, data: dict[str, Any]) -> str:
    path = PROMPTS_DIR / template
    return path.read_text(encoding="utf-8").replace(
        "{{ data_json }}", json.dumps(data, default=str, indent=2)
    )


def _fallback_teaser() -> InvestmentTeaser:
    return InvestmentTeaser(
        problem="The simulation data shows a market opportunity with execution risk.",
        solution="The product addresses the identified market need.",
        simulated_survival="Simulation results available in the full report.",
        key_metrics=["MRR: see report", "CAC: see report", "Runway: see report"],
        ask="Funding ask detailed in the full report.",
        risks=["Execution risk"],
    )


def _fallback_outline() -> PitchDeckOutline:
    order = [
        "Problem", "Solution", "Market", "Product", "Business Model",
        "Traction/Simulation", "Financial Projections", "Unit Economics",
        "Competition", "Team", "Ask", "Use of Funds",
    ]
    return PitchDeckOutline(
        slides=[
            PitchSlide(
                slide_number=i + 1,
                title=title,
                talking_points=[f"Key point for {title}."],
            )
            for i, title in enumerate(order)
        ]
    )


def _register_mock_outputs(provider: Any) -> None:
    """Pin deterministic canned outputs for the mock provider (dev/test)."""
    from app.agents.llm.base import MockProvider

    if not isinstance(provider, MockProvider):
        return
    provider.register(
        "Generate the investment teaser",
        json.dumps(
            {
                "problem": "The market is underserved by current solutions.",
                "solution": "Our platform addresses the gap with a focused product.",
                "simulated_survival": "68% 24-month survival across simulated runs.",
                "key_metrics": ["MRR $12k", "CAC $450", "LTV/CAC 3.1", "Runway 18mo"],
                "ask": "Raising $500K to extend runway.",
                "risks": ["High CAC", "Market timing"],
            }
        ),
    )
    provider.register(
        "Generate the pitch deck outline",
        json.dumps(
            {
                "slides": [
                    {
                        "slide_number": i + 1,
                        "title": title,
                        "talking_points": ["Grounded in simulation data."],
                    }
                    for i, title in enumerate(
                        [
                            "Problem", "Solution", "Market", "Product", "Business Model",
                            "Traction/Simulation", "Financial Projections", "Unit Economics",
                            "Competition", "Team", "Ask", "Use of Funds",
                        ]
                    )
                ]
            }
        ),
    )


def _get_provider() -> Any:
    from app.agents.llm.factory import get_llm_provider

    provider = get_llm_provider(get_settings())
    _register_mock_outputs(provider)
    return provider


async def generate_teaser(data: dict[str, Any]) -> InvestmentTeaser:
    prompt = _load_prompt("investment_teaser.md", data)
    try:
        result = await bridge.generate_structured(
            _get_provider(),
            InvestmentTeaser,
            prompt,
            "Generate the investment teaser.",
            temperature=0.3,
        )
    except StructuredOutputError:
        logger.warning("investor tools: teaser generation failed, using fallback")
        return _fallback_teaser()
    logger.info("investor tools: investment teaser generated")
    return result


async def generate_pitch_outline(data: dict[str, Any]) -> PitchDeckOutline:
    prompt = _load_prompt("pitch_deck_outline.md", data)
    try:
        result = await bridge.generate_structured(
            _get_provider(),
            PitchDeckOutline,
            prompt,
            "Generate the pitch deck outline.",
            temperature=0.3,
        )
    except StructuredOutputError:
        logger.warning("investor tools: pitch outline failed, using fallback")
        return _fallback_outline()
    logger.info("investor tools: pitch deck outline generated, slides=%s", len(result.slides))
    return result


def teaser_to_pdf(teaser: InvestmentTeaser, workspace_name: str, run_id: str) -> bytes:
    """Convert InvestmentTeaser to a PDF page."""
    content = f"""# Investment Teaser — {workspace_name}

## The Problem
{teaser.problem}

## Our Solution
{teaser.solution}

## Simulation Validation
{teaser.simulated_survival}

## Key Metrics
{chr(10).join(f'- {m}' for m in teaser.key_metrics)}

## The Ask
{teaser.ask}

## Key Risks
{chr(10).join(f'- {r}' for r in teaser.risks)}
"""
    section = {"section_number": 1, "title": "Investment Teaser", "narrative": content}
    return assemble_pdf(
        sections=[section],
        chart_paths={},
        workspace_name=workspace_name,
        run_id=run_id,
        tier="pro",
        report_type="investor_report",
    )


def pitch_outline_to_pdf(outline: PitchDeckOutline, workspace_name: str, run_id: str) -> bytes:
    slides_md = ""
    for slide in outline.slides:
        slides_md += f"\n## Slide {slide.slide_number}: {slide.title}\n"
        for pt in slide.talking_points:
            slides_md += f"- {pt}\n"
    section = {"section_number": 1, "title": "Pitch Deck Outline", "narrative": slides_md}
    return assemble_pdf(
        sections=[section],
        chart_paths={},
        workspace_name=workspace_name,
        run_id=run_id,
        tier="pro",
        report_type="investor_report",
    )
