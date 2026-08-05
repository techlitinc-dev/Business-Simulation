"""Forge agent unit tests (T22)."""

import json
from pathlib import Path

from app.agents.forge import _SYSTEM_PROMPT, ForgeAgent
from app.agents.llm.base import MockProvider
from app.schemas.blueprint import ForgeReviewResponse

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


def _canned_review() -> str:
    return json.dumps(
        {
            "overall_assessment": "Strong model but runway is tight.",
            "identified_vulnerabilities": [
                {
                    "type": "liquidity",
                    "severity": "high",
                    "description": "Burn exceeds capital runway.",
                    "mitigation_suggestion": "Cut fixed costs.",
                }
            ],
        }
    )


async def test_forge_system_prompt_has_spec_content() -> None:
    content = _SYSTEM_PROMPT
    assert "NEVER BE GENERIC" in content
    assert "FORMAT B: DYNAMIC HURDLE GENERATION" in content


async def test_review_returns_schema_and_uses_only_bridge() -> None:
    provider = MockProvider()
    provider.register("BLUEPRINT", _canned_review())

    agent = ForgeAgent(provider)
    review, response = await agent.review_blueprint(_payload(), reviewed_version=1)

    assert isinstance(review, ForgeReviewResponse)
    assert review.reviewed_version == 1
    assert review.overall_assessment
    assert review.identified_vulnerabilities[0].type == "liquidity"
    assert response.model == provider.model
    # ForgeAgent must not call provider.complete directly — the bridge owns calls.
    # (grep in the task card; we assert here that the bridge path is exercised.)
    assert review.llm_model == provider.model


async def test_review_repair_loop_recovers() -> None:
    provider = MockProvider()
    # The repair prompt contains "failed validation" but also embeds the original
    # request (which contains "BLUEPRINT") — register the repair response FIRST
    # so first-match-wins picks it for the repair call.
    provider.register("failed validation", _canned_review())
    provider.register("BLUEPRINT", json.dumps([1, 2, 3]))

    agent = ForgeAgent(provider)
    review, _ = await agent.review_blueprint(_payload(), reviewed_version=1)
    assert review.identified_vulnerabilities[0].severity == "high"
