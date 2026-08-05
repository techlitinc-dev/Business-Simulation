"""Structured-output bridge tests (T21): extraction, repair loop, clamping."""

import json

import pytest
from app.agents.bridge import clamp_deltas, extract_json, generate_structured
from app.agents.llm.base import LLMResponse
from app.core.exceptions import StructuredOutputError
from pydantic import BaseModel, Field


class Widget(BaseModel):
    name: str
    value: float
    believability_score: float = Field(ge=0, le=1)
    cac_delta_percent: float = 0.0


class StubProvider:
    """Test provider with a queue of canned responses + a call log."""

    def __init__(self, responses: list[str], model: str = "stub") -> None:
        self._responses = list(responses)
        self.model = model
        self.calls: list[tuple[str, str]] = []

    async def complete(
        self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048
    ) -> LLMResponse:
        self.calls.append((system, user))
        content = self._responses.pop(0) if self._responses else "{}"
        return LLMResponse(
            content=content, model=self.model, prompt_tokens=1, completion_tokens=1,
            cost_usd=0.0, latency_ms=1.0,
        )


def _valid() -> str:
    return json.dumps({"name": "w", "value": 1.5, "believability_score": 0.8})


# --- extraction --------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ('{"a": 1}', '{"a": 1}'),
        ('```json\n{"a": 1}\n```', '{"a": 1}'),
        ('```\n{"a": 1}\n```', '{"a": 1}'),
        ('Here is the output:\n{"a": 1}\nHope it helps.', '{"a": 1}'),
        ('{"a": 1}', '{"a": 1}'),
    ],
)
def test_extract_json(raw: str, expected: str) -> None:
    assert extract_json(raw) == expected


async def test_valid_first_attempt_single_call() -> None:
    provider = StubProvider([_valid()])
    result = await generate_structured(provider, Widget, "sys", "user")
    assert result.name == "w"
    assert len(provider.calls) == 1


async def test_prose_wrapped_parsed() -> None:
    provider = StubProvider([f"Sure thing:\n{_valid()}\n\nLet me know!"])
    result = await generate_structured(provider, Widget, "sys", "user")
    assert result.name == "w"


# --- repair loop -------------------------------------------------------------


async def test_repair_recovers_after_invalid_json() -> None:
    provider = StubProvider(["not json at all", _valid()])
    result = await generate_structured(provider, Widget, "sys", "user")
    assert result.name == "w"
    assert len(provider.calls) == 2
    # The repair prompt mentions the validation error and the schema.
    repair_prompt = provider.calls[1][1]
    assert "Invalid output received" in repair_prompt
    assert '"name"' in repair_prompt  # schema JSON embedded


async def test_repair_recovers_after_schema_violation() -> None:
    # Missing required field "value" -> ValidationError, not clampable -> repair.
    provider = StubProvider(
        [json.dumps({"name": "w", "believability_score": 0.8}), _valid()]
    )
    result = await generate_structured(provider, Widget, "sys", "user")
    assert result.name == "w"
    assert result.value == pytest.approx(1.5)
    assert len(provider.calls) == 2


async def test_always_invalid_raises_after_max_repairs() -> None:
    provider = StubProvider(["garbage"] * 10)
    with pytest.raises(StructuredOutputError) as exc_info:
        await generate_structured(provider, Widget, "sys", "user", max_repairs=2)
    assert exc_info.value.raw_output == "garbage"
    # 1 initial + 2 repairs
    assert len(provider.calls) == 3


# --- clamping ----------------------------------------------------------------


def test_clamp_deltas_nested_and_suffix() -> None:
    data = {
        "cac_delta_percent": 500,
        "team_morale_delta": -3.0,
        "nested": {"churn_delta_percent": -200},
    }
    result = clamp_deltas(data)
    assert result["cac_delta_percent"] == 200.0
    assert result["team_morale_delta"] == -1.0
    assert result["nested"]["churn_delta_percent"] == -90.0
    # input not mutated
    assert data["cac_delta_percent"] == 500


def test_clamp_deltas_leaves_in_range_and_non_matching() -> None:
    data = {"cac_delta_percent": 10, "name": "x", "count": 5}
    result = clamp_deltas(data)
    assert result["cac_delta_percent"] == 10.0
    assert result["name"] == "x"
    assert result["count"] == 5


async def test_clamp_applied_before_validation() -> None:
    provider = StubProvider(
        [json.dumps({"name": "w", "value": 1.5, "believability_score": 1.7})]
    )
    result = await generate_structured(provider, Widget, "sys", "user")
    assert result.believability_score == 1.0
    assert len(provider.calls) == 1


async def test_clamp_disabled_rejects_out_of_range() -> None:
    provider = StubProvider(
        [json.dumps({"name": "w", "value": 1.5, "believability_score": 1.7})]
    )
    with pytest.raises(StructuredOutputError):
        await generate_structured(provider, Widget, "sys", "user", clamp=False, max_repairs=0)
