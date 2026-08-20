from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from app.agents import bridge
from app.core.config import get_settings
from app.core.exceptions import StructuredOutputError
from app.schemas.advisory import BoardSummary, PersonaReview

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

PERSONA_CONFIG = [
    ("CFO", "cfo_persona.md"),
    ("CMO", "cmo_persona.md"),
    ("RiskAuditor", "risk_auditor_persona.md"),
    ("Operator", "operator_persona.md"),
]


def _load_persona_prompt(template_name: str, data: dict[str, Any]) -> str:
    path = PROMPTS_DIR / template_name
    template = path.read_text(encoding="utf-8")
    return template.replace("{{ data_json }}", json.dumps(data, default=str, indent=2))


def _fallback_review(persona: str) -> PersonaReview:
    """Deterministic schema-valid review when the LLM is unavailable."""
    return PersonaReview(
        persona=persona,
        verdict=f"{persona} review generated from simulation data.",
        top_concerns=["Cash runway requires close monitoring"],
        opportunities=["Optimize unit economics"],
        questions_for_founder=["What is the primary driver of the top concern?"],
        confidence_level="MEDIUM",
    )


def _fallback_summary() -> BoardSummary:
    return BoardSummary(
        consensus_verdict="The model needs tighter financial controls.",
        points_of_agreement=["Runway and unit economics are the key risks"],
        points_of_conflict=["Growth vs. profitability trade-off"],
        top_priority_action="Extend the cash runway before scaling spend",
        overall_risk_level="MEDIUM",
    )


def _register_mock_outputs(provider: Any) -> None:
    """Pin deterministic canned outputs for the mock provider (dev/test)."""
    from app.agents.llm.base import MockProvider

    if not isinstance(provider, MockProvider):
        return
    for persona in ("CFO", "CMO", "RiskAuditor", "Operator"):
        provider.register(
            f"Provide your {persona} review",
            json.dumps(
                {
                    "persona": persona,
                    "verdict": f"{persona} verdict on the simulation.",
                    "top_concerns": ["Cash burn", "Unit economics", "Concentration"],
                    "opportunities": ["Improve CAC payback"],
                    "questions_for_founder": ["How does churn trend next quarter?"],
                    "confidence_level": "MEDIUM",
                }
            ),
        )
    provider.register(
        "Synthesize the board reviews",
        json.dumps(
            {
                "consensus_verdict": "Runway is the binding constraint.",
                "points_of_agreement": ["Extend runway", "Fix unit economics"],
                "points_of_conflict": ["Growth spend vs. profitability"],
                "top_priority_action": "Reduce burn before scaling",
                "overall_risk_level": "MEDIUM",
            }
        ),
    )


async def _get_persona_review(
    persona: str, template: str, data: dict[str, Any]
) -> PersonaReview:
    from app.agents.llm.factory import get_llm_provider

    provider = get_llm_provider(get_settings())
    _register_mock_outputs(provider)
    prompt = _load_persona_prompt(template, data)
    try:
        result = await bridge.generate_structured(
            provider,
            PersonaReview,
            prompt,
            f"Provide your {persona} review of this business simulation.",
            temperature=0.3,
        )
    except StructuredOutputError:
        logger.warning(
            "advisory board: persona review failed, using fallback (persona=%s)",
            persona,
        )
        return _fallback_review(persona)
    # Override persona field to match config (MockProvider may return wrong value).
    result_dict = result.model_dump()
    result_dict["persona"] = persona
    return PersonaReview(**result_dict)


async def _synthesize_board(
    reviews: list[PersonaReview], data: dict[str, Any]
) -> BoardSummary:
    from app.agents.llm.factory import get_llm_provider

    provider = get_llm_provider(get_settings())
    _register_mock_outputs(provider)
    reviews_json = json.dumps([r.model_dump() for r in reviews], indent=2)
    summary_fields = {k: v for k, v in data.items() if k in ["survival_rate", "resilience_score"]}
    prompt = f"""You are synthesizing 4 advisory board reviews into a unified BoardSummary.

INDIVIDUAL REVIEWS:
{reviews_json}

BUSINESS DATA SUMMARY:
{json.dumps(summary_fields, indent=2)}

Identify: consensus_verdict, points_of_agreement (issues all/most agree on),
points_of_conflict (issues where personas disagree), top_priority_action, overall_risk_level.
"""
    try:
        return await bridge.generate_structured(
            provider,
            BoardSummary,
            prompt,
            "Synthesize the board reviews.",
            temperature=0.2,
        )
    except StructuredOutputError:
        logger.warning("advisory board: synthesis failed, using fallback")
        return _fallback_summary()


async def run_advisory_board(
    blueprint_payload: dict[str, Any],
    run_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Run 4 persona reviews in parallel, then synthesize a BoardSummary.
    Returns {"reviews": [...], "summary": {...}}.
    """
    data = {**blueprint_payload, **run_summary}

    reviews = list(
        await asyncio.gather(
            *[_get_persona_review(persona, template, data) for persona, template in PERSONA_CONFIG]
        )
    )

    summary = await _synthesize_board(reviews, run_summary)

    logger.info("advisory board: review complete, risk_level=%s", summary.overall_risk_level)
    return {
        "reviews": [r.model_dump() for r in reviews],
        "summary": summary.model_dump(),
    }
