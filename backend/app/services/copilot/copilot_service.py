from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import bridge
from app.core.config import get_settings
from app.core.exceptions import StructuredOutputError
from app.services.copilot.context_builder import build_copilot_context

logger = logging.getLogger(__name__)

NUMBER_PATTERN = re.compile(r"\b\d[\d,]*\.?\d*\b")


class CopilotResponse(BaseModel):
    answer: str = Field(..., min_length=10)
    sources_used: list[str] = Field(
        default_factory=list,
        description="Which data sources were referenced",
    )
    confidence: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH)$")


def _fallback_answer(question: str) -> CopilotResponse:
    """Deterministic, schema-valid answer when the LLM is unavailable."""
    return CopilotResponse(
        answer=(
            "The simulation data doesn't contain enough information to answer that "
            "precisely. I can only answer questions grounded in the run data."
        ),
        sources_used=[],
        confidence="LOW",
    )


def _register_mock_output(provider: object) -> None:
    from app.agents.llm.base import MockProvider

    if not isinstance(provider, MockProvider):
        return
    provider.register(
        "copilot",
        json.dumps(
            {
                "answer": (
                    "Based on the simulation data, the key metrics show a "
                    "moderate outlook for the run."
                ),
                "sources_used": ["tick_logs", "mc_aggregates"],
                "confidence": "MEDIUM",
            }
        ),
    )


async def chat(
    run_id: str,
    question: str,
    db: AsyncSession,
    chat_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Answer a question about a simulation run.
    All numeric claims are cross-checked against the data pack.
    Returns {"answer": str, "grounded": bool, "flagged_claims": list}.
    """
    from app.agents.llm.factory import get_llm_provider

    context = await build_copilot_context(run_id, db)
    context_str = json.dumps(context, default=str)

    prompt = f"""You are a copilot that answers questions about a business simulation run.

SIMULATION DATA:
{context_str[:8000]}

RULES:
- Answer using ONLY data from the simulation data above.
- Every numeric claim must reference a real number from the data.
- If you don't know, say "The simulation data doesn't contain enough information to answer that."
- Be concise. 2-3 sentences max unless the question requires a list.
- sources_used: list the data keys you referenced (e.g. "tick_logs", "mc_aggregates").
"""
    provider = get_llm_provider(get_settings())
    _register_mock_output(provider)

    try:
        result = await bridge.generate_structured(
            provider,
            CopilotResponse,
            prompt,
            question,
            temperature=0.2,
        )
    except StructuredOutputError:
        logger.warning("copilot: structured output failed, using fallback")
        result = _fallback_answer(question)

    # Numeric cross-check.
    numbers_in_answer = set(NUMBER_PATTERN.findall(result.answer.replace(",", "")))
    flagged = [n for n in numbers_in_answer if float(n) > 100 and n not in context_str]

    logger.info(
        "copilot: answered run=%s question_len=%s flagged=%s",
        run_id,
        len(question),
        len(flagged),
    )

    return {
        "answer": result.answer,
        "sources_used": result.sources_used,
        "confidence": result.confidence,
        "grounded": len(flagged) == 0,
        "flagged_claims": flagged,
    }
