"""Unit tests for the simulation copilot service (Day 17)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.services.copilot.copilot_service import NUMBER_PATTERN, CopilotResponse, chat


def test_number_pattern_extracts_large_numbers() -> None:
    text = "Revenue was $125,000 and cash was 86000 in month 3."
    nums = set(NUMBER_PATTERN.findall(text.replace(",", "")))
    assert "125000" in nums or "125" in nums
    assert "86000" in nums


async def test_chat_returns_required_keys() -> None:
    with patch(
        "app.services.copilot.copilot_service.build_copilot_context",
        new_callable=AsyncMock,
    ) as mock_ctx:
        mock_ctx.return_value = {"tick_logs": [], "mc_aggregates": {"survival_rate": 0.68}}
        result = await chat("run_001", "What is the survival rate?", AsyncMock())
    assert "answer" in result
    assert "grounded" in result
    assert "flagged_claims" in result
    assert isinstance(result["flagged_claims"], list)
    assert result["confidence"] in ("LOW", "MEDIUM", "HIGH")


async def test_chat_grounded_when_no_suspicious_numbers() -> None:
    with (
        patch(
            "app.services.copilot.copilot_service.build_copilot_context",
            new_callable=AsyncMock,
        ) as mock_ctx,
        patch(
            "app.agents.bridge.generate_structured",
            new_callable=AsyncMock,
        ) as mock_gen,
    ):
        mock_ctx.return_value = {"mc_aggregates": {"survival_rate": 0.68}}
        mock_gen.return_value = CopilotResponse(
            answer="The survival rate is 68 percent.",
            sources_used=["mc_aggregates"],
            confidence="HIGH",
        )
        result = await chat("run_001", "What is the survival rate?", AsyncMock())
    # 68 is <=100, so not flagged.
    assert result["grounded"] is True
    assert result["flagged_claims"] == []


async def test_chat_flags_ungrounded_large_numbers() -> None:
    with (
        patch(
            "app.services.copilot.copilot_service.build_copilot_context",
            new_callable=AsyncMock,
        ) as mock_ctx,
        patch(
            "app.agents.bridge.generate_structured",
            new_callable=AsyncMock,
        ) as mock_gen,
    ):
        mock_ctx.return_value = {"mc_aggregates": {"survival_rate": 0.68}}
        mock_gen.return_value = CopilotResponse(
            answer="Revenue reached 999999 dollars this month.",
            sources_used=["tick_logs"],
            confidence="HIGH",
        )
        result = await chat("run_001", "What is revenue?", AsyncMock())
    assert result["grounded"] is False
    assert "999999" in result["flagged_claims"]


async def test_chat_falls_back_when_provider_invalid() -> None:
    # Unregistered MockProvider returns "{}" -> StructuredOutputError -> fallback.
    with patch(
        "app.services.copilot.copilot_service.build_copilot_context",
        new_callable=AsyncMock,
    ) as mock_ctx:
        mock_ctx.return_value = {"mc_aggregates": {"survival_rate": 0.68}}
        result = await chat("run_001", "What is the survival rate?", AsyncMock())
    assert "doesn't contain enough information" in result["answer"]
    assert result["grounded"] is True
