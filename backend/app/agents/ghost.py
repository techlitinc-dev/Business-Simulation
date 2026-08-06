"""GhostAgent — autonomous AI decision-maker for Ghost Mode (T43).

Every decision goes through the provider abstraction + bridge. When the
provider is the deterministic mock (no API key), the agent enforces a fixed
personality rule on the validated options so tests are stable. In live mode
the LLM's pick is trusted.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agents import bridge
from app.agents.llm.base import LLMProvider
from app.agents.llm.factory import provider_is_mock

GhostPersonality = Literal["aggressive", "conservative", "opportunist"]

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "ghost_personality.md").read_text(
    encoding="utf-8"
)


class GhostDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: str = Field(min_length=1)
    rationale: str = Field(max_length=500)


class GhostAgent:
    def __init__(
        self,
        provider: LLMProvider,
        personality: GhostPersonality,
        on_response: Callable[[Any], Any] | None = None,
    ) -> None:
        self._provider = provider
        self._personality = personality
        self._on_response = on_response

    async def choose_option(
        self,
        hurdle: dict[str, Any],
        state_snapshot: dict[str, Any],
    ) -> GhostDecision:
        """Pick an option for the hurdle — bridge-validated, rule-backed in mock mode."""
        options = hurdle.get("strategic_options", [])
        if not options:
            raise ValueError("Hurdle has no strategic_options")

        system_prompt = _SYSTEM_PROMPT.replace("{{personality}}", self._personality)
        user_prompt = (
            "Choose the best strategic option for this hurdle.\n\n"
            f"HURDLE:\n{json.dumps(hurdle, indent=2)}\n\n"
            f"VITAL SIGNS:\n{json.dumps(state_snapshot, indent=2)}\n\n"
            "Return ONLY the {\"option_id\", \"rationale\"} JSON."
        )

        decision = await bridge.generate_structured(
            self._provider,
            GhostDecision,
            system_prompt,
            user_prompt,
            temperature=0.2,
            clamp=False,
            on_response=self._on_response,
        )

        # Deterministic rule override in mock mode: the mock always returns a
        # fixed option, so enforce the personality rule to keep tests stable.
        if provider_is_mock(self._provider):
            return GhostDecision(
                option_id=self._rule_choice(options),
                rationale=self._rule_rationale(options),
            )

        # Validate the LLM's option_id actually exists; fall back to the rule.
        if decision.option_id not in {o.get("option_id") for o in options}:
            return GhostDecision(
                option_id=self._rule_choice(options),
                rationale=self._rule_rationale(options),
            )
        return decision

    # ------------------------------------------------------------------ #
    # Deterministic personality rules (mock mode / fallback)
    # ------------------------------------------------------------------ #

    def _rule_choice(self, options: list[dict[str, Any]]) -> str:
        scored: list[tuple[str, float, float]] = [
            (
                str(o.get("option_id", "")),
                float(o.get("probability_success", 0.0) or 0.0),
                float(o.get("cash_impact_monthly", 0.0) or 0.0),
            )
            for o in options
        ]
        if self._personality == "aggressive":
            best: tuple[str, float, float] = max(scored, key=lambda t: (t[1], t[2]))
        elif self._personality == "conservative":
            # Smallest negative cash impact = highest (closest to zero) cash value.
            best = max(scored, key=lambda t: (t[2], t[1]))
        else:  # opportunist — maximize expected value
            best = max(scored, key=lambda t: t[1] * t[2])
        return best[0]

    def _rule_rationale(self, options: list[dict[str, Any]]) -> str:
        choice = self._rule_choice(options)
        chosen = next((o for o in options if o.get("option_id") == choice), {})
        name = chosen.get("name", choice)
        return (
            f"{self._personality} play: {name} — best match for the "
            f"{self._personality} decision rule."
        )
