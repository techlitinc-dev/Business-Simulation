"""Structured-output bridge: LLM -> validated Pydantic models with repair-retry.

Every agent LLM call funnels through ``generate_structured``. Raw model output
is JSON-extracted (markdown fences / surrounding prose stripped), clamped
(mechanical deltas tamed to physical possibility), and validated against a
Pydantic v2 schema; invalid output triggers a repair-retry loop (default 2
repairs) before failing with ``StructuredOutputError``.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from app.agents.llm.base import LLMProvider, LLMResponse
from app.core.exceptions import StructuredOutputError

#: Mechanical bounds the bridge applies before schema validation (plan.md Risks).
MECHANICAL_DELTA_BOUNDS: dict[str, tuple[float, float]] = {
    "_delta_percent": (-90.0, 200.0),
    "team_morale_delta": (-1.0, 1.0),
    "probability_success": (0.0, 1.0),
    "believability_score": (0.0, 1.0),
}


def clamp_deltas(
    data: dict[str, Any], bounds: dict[str, tuple[float, float]] = MECHANICAL_DELTA_BOUNDS
) -> dict[str, Any]:
    """Deep-copy ``data`` and clamp numeric fields whose name matches a bound.

    A field matches if its name is exactly a bound key or ends with that key as
    a suffix (e.g. ``cac_delta_percent`` matches ``_delta_percent``). The input
    dict is never mutated.
    """
    result = copy.deepcopy(data)
    for key, value in result.items():
        if isinstance(value, dict):
            result[key] = clamp_deltas(value, bounds)
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        for bound_key, (lo, hi) in bounds.items():
            if key == bound_key or key.endswith(bound_key):
                result[key] = max(lo, min(hi, float(value)))
                break
    return result


def extract_json(raw: str) -> str:
    """Extract the JSON payload from raw model output.

    Strips ```json / ``` code fences and, when prose surrounds the JSON,
    slices from the first ``{`` to the last ``}``.
    """
    content = raw.strip()
    if content.startswith("```"):
        # Strip the opening fence (and any language tag) + closing fence.
        lines = content.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    if content and content[0] == "{" and content[-1] == "}":
        return content
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        return content[start : end + 1]
    return content


async def generate_structured[T: BaseModel](
    provider: LLMProvider,
    schema: type[T],
    system_prompt: str,
    user_prompt: str,
    *,
    max_repairs: int = 2,
    temperature: float = 0.2,
    clamp: bool = True,
    on_response: Callable[[LLMResponse], Any] | None = None,
) -> T:
    """Call the provider, then validate/repair until the result fits ``schema``."""
    result, _ = await generate_structured_with_response(
        provider,
        schema,
        system_prompt,
        user_prompt,
        max_repairs=max_repairs,
        temperature=temperature,
        clamp=clamp,
        on_response=on_response,
    )
    return result


async def generate_structured_with_response[T: BaseModel](
    provider: LLMProvider,
    schema: type[T],
    system_prompt: str,
    user_prompt: str,
    *,
    max_repairs: int = 2,
    temperature: float = 0.2,
    clamp: bool = True,
    on_response: Callable[[LLMResponse], Any] | None = None,
) -> tuple[T, LLMResponse]:
    """Like ``generate_structured`` but also returns the last provider response
    (for token/cost reporting by callers such as the Forge review endpoint).

    ``on_response`` is invoked with every provider response (including repair
    attempts) — services use it to meter LLM tokens (T41).
    """
    schema_json = schema.model_json_schema()
    last_response: LLMResponse | None = None

    async def _complete(prompt: str) -> str:
        nonlocal last_response
        last_response = await provider.complete(system_prompt, prompt, temperature=temperature)
        if on_response is not None:
            result = on_response(last_response)
            if result is not None and hasattr(result, "__await__"):
                await result
        return last_response.content

    raw = await _complete(user_prompt)
    attempts_left = max_repairs
    while True:
        try:
            parsed = json.loads(extract_json(raw))
            if not isinstance(parsed, dict):
                raise ValueError("top-level JSON is not an object")
            if clamp:
                parsed = clamp_deltas(parsed)
            assert last_response is not None
            return schema.model_validate(parsed), last_response
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            if attempts_left <= 0:
                raise StructuredOutputError(raw_output=raw, validation_error=exc) from exc
            attempts_left -= 1
            repair_prompt = (
                f"Your previous response failed validation. Fix ONLY the JSON.\n\n"
                f"Original request:\n{user_prompt}\n\n"
                f"Invalid output received:\n{raw}\n\n"
                f"Validation error:\n{exc}\n\n"
                f"Target JSON schema:\n{json.dumps(schema_json, indent=2)}\n\n"
                "Return corrected JSON only — no prose, no markdown fences."
            )
            raw = await _complete(repair_prompt)
