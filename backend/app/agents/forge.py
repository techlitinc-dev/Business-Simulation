"""Forge agent — blueprint review (Format A vulnerabilities)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agents import bridge
from app.agents.llm.base import LLMProvider, LLMResponse
from app.schemas.blueprint import ForgeReviewLLMResponse, ForgeReviewResponse

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "forge_system.md").read_text(
    encoding="utf-8"
)


class ForgeAgent:
    """The Architect & Game Master. Reviews blueprints for structural weaknesses."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def review_blueprint(
        self, blueprint_payload: dict[str, Any], *, reviewed_version: int = 1
    ) -> tuple[ForgeReviewResponse, LLMResponse]:
        pretty = json.dumps(blueprint_payload, indent=2)
        user_prompt = (
            "Review this business blueprint and identify its structural vulnerabilities.\n\n"
            f"BLUEPRINT (Format A JSON):\n{pretty}\n\n"
            "Output ONLY a JSON object with exactly these fields:\n"
            '- "overall_assessment": a 2-3 sentence honest assessment '
            "(spec §13: be brutally honest, quantify)\n"
            '- "identified_vulnerabilities": a list of vulnerability objects, each with '
            '"type" (liquidity|concentration|unit_economics|market|operational|team|regulatory), '
            '"severity" (low|medium|high|critical), "description", and "mitigation_suggestion"\n'
            "No prose around the JSON. No markdown fences."
        )
        llm_review, response = await bridge.generate_structured_with_response(
            self._provider,
            ForgeReviewLLMResponse,
            _SYSTEM_PROMPT,
            user_prompt,
            temperature=0.2,
        )
        review = ForgeReviewResponse(
            overall_assessment=llm_review.overall_assessment,
            identified_vulnerabilities=llm_review.identified_vulnerabilities,
            reviewed_version=reviewed_version,
            llm_model=response.model,
            tokens_used=response.prompt_tokens + response.completion_tokens,
        )
        return review, response
