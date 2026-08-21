"""Playbook writer — turns a post-mortem analysis into a reusable playbook.

Follows the section_writer pattern: render the prompt template, call the
provider through the structured-output bridge, and fall back to a
deterministic playbook when the LLM is unavailable (mock provider returns
``{}``), so the endpoint never 500s in dev/test.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.agents import bridge
from app.agents.llm.base import LLMProvider
from app.core.config import get_settings
from app.core.exceptions import StructuredOutputError

logger = logging.getLogger("forge.playbook_writer")

PROMPTS_DIR = Path(__file__).parent / "prompts"


class Playbook(BaseModel):
    title: str = Field(
        ..., description="e.g. 'Surviving a Demand Shock as a Subscription Business'"
    )
    scenario_type: str
    situation: str = Field(..., description="2-3 sentences describing when to use this playbook")
    steps: list[str] = Field(..., min_length=3, max_length=10, description="Ordered action steps")
    key_metrics_to_watch: list[str] = Field(..., min_length=2)
    expected_outcome: str
    source_run_summary: str


def _load_prompt() -> str:
    prompt_path = PROMPTS_DIR / "playbook_writer.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return (
        "You are writing a reusable business playbook from a post-mortem "
        "simulation analysis.\nDATA: {{ data_json }}\n"
        "Generate a Playbook schema object."
    )


def _make_provider() -> LLMProvider:
    from app.agents.llm.factory import get_llm_provider

    return get_llm_provider(get_settings())


def _fallback_playbook(
    post_mortem_data: Mapping[str, Any], run_summary: Mapping[str, Any]
) -> Playbook:
    """Deterministic playbook built from the data pack (no LLM)."""
    deltas = post_mortem_data.get("optimization_entries", []) or []
    top = deltas[0].get("tweak_key", "core operations") if deltas else "core operations"
    events = post_mortem_data.get("events_decisions", {}) or {}
    events_list = events.get("events", [])
    scenario = (
        events_list[0].get("payload", {}).get("category", "market")
        if events_list
        else "market"
    )
    return Playbook(
        title=f"Playbook: {scenario.replace('_', ' ').title()} resilience",
        scenario_type=scenario,
        situation=(
            "Use this playbook when the simulation surfaced a "
            f"{scenario.replace('_', ' ')} shock that threatened the runway."
        ),
        steps=[
            f"Address the top kill vector first: {top}.",
            "Cut discretionary spend to extend the cash runway.",
            "Re-negotiate vendor contracts within 30 days.",
            "Review unit economics weekly until the shock passes.",
        ],
        key_metrics_to_watch=["cash_balance", "monthly_burn", "runway_months"],
        expected_outcome=(
            "A stabilized runway and a return to positive operating momentum."
        ),
        source_run_summary=run_summary.get("summary", "Deterministic fallback"),
    )


async def generate_playbook(
    post_mortem_data: Mapping[str, Any], run_summary: Mapping[str, Any]
) -> Playbook:
    """Generate a reusable playbook from post-mortem + run data."""
    provider = _make_provider()
    template = _load_prompt()
    data_json = json.dumps(
        {**post_mortem_data, **run_summary}, default=str, indent=2
    )
    prompt = template.replace("{{ data_json }}", data_json)

    try:
        result = await bridge.generate_structured(
            provider,
            Playbook,
            prompt,
            "Generate a reusable playbook from this post-mortem.",
            temperature=0.4,
        )
    except StructuredOutputError:
        logger.warning("[playbook_writer] LLM output invalid — using fallback playbook")
        return _fallback_playbook(post_mortem_data, run_summary)

    logger.info("[playbook_writer] Generated playbook: %s", result.title)
    return result
