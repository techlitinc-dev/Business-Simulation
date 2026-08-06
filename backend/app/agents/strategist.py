"""Strategist — branching options + deterministic 12-month projections (spec §8).

``propose_options`` calls the LLM (via the bridge); ``project_option`` is pure
deterministic engine math — no LLM, no I/O.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.agents import bridge
from app.agents.chronicle import Chronicle
from app.agents.hurdle_generator import build_vital_signs
from app.agents.llm.base import LLMProvider
from app.engine.events import apply_event
from app.engine.loop import tick
from app.engine.state import BusinessState
from app.schemas.decision import (
    OptionProjection,
    StrategicOption,
    StrategicOptionList,
    StrategistResult,
)
from app.schemas.hurdle import HurdleEvent

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "strategic_options.md").read_text(
    encoding="utf-8"
)


class Strategist:
    def __init__(
        self,
        provider: LLMProvider,
        on_response: Callable[[Any], Any] | None = None,
    ) -> None:
        self._provider = provider
        self._on_response = on_response

    async def propose_options(
        self,
        state: BusinessState,
        kpis: dict[str, Any],
        hurdle: HurdleEvent,
        chronicle: Chronicle,
    ) -> list[StrategicOption]:
        vital = build_vital_signs(state, kpis)
        user_prompt = (
            "Advise on this hurdle. Propose 2-4 strategically distinct options.\n\n"
            f"VITAL SIGNS:\n{json.dumps(vital, indent=2)}\n\n"
            f"HURDLE:\n{json.dumps(hurdle.model_dump(mode='json'), indent=2)}\n\n"
            f"SIMULATION CHRONICLE:\n{chronicle.to_prompt_summary()}\n\n"
            "Output ONLY the {\"options\": [...]} JSON described in your instructions."
        )
        result = await bridge.generate_structured(
            self._provider,
            StrategicOptionList,
            _SYSTEM_PROMPT,
            user_prompt,
            temperature=0.6,
            clamp=True,
            on_response=self._on_response,
        )
        return result.options

    def project_option(
        self,
        state: BusinessState,
        option: StrategicOption,
        hurdle: HurdleEvent,
        *,
        months: int = 12,
        seed: int = 0,
    ) -> OptionProjection:
        """Deterministic 12-month cash projection for one option. Pure engine math."""
        rng = random.Random(seed)
        sim = state.snapshot()

        # Apply the hurdle's mechanical impact first (if not already applied),
        # then the option's monthly cash impact on top.
        impact = hurdle.mechanical_impact.model_dump(mode="json")
        if impact.get("immediate") and any(
            v is not None for v in impact["immediate"].values()
        ):
            sim = apply_event(sim, impact, month=sim.month + 1)

        monthly_cash: list[float] = []
        cash = sim.financials.cash
        for _ in range(months):
            sim = tick(sim, rng)
            sim.financials.cash += option.cash_impact_monthly
            cash = sim.financials.cash
            monthly_cash.append(round(cash, 2))
            if sim.bankrupt:
                break

        # Pad the remaining months with the terminal cash (bankrupt -> stays).
        if len(monthly_cash) < months:
            monthly_cash.extend([monthly_cash[-1]] * (months - len(monthly_cash)))

        min_cash = min(monthly_cash)
        end_cash = monthly_cash[-1]
        burn = sim.financials.monthly_burn
        runway = end_cash / burn if burn > 0 else float("inf")
        return OptionProjection(
            option_id=option.option_id,
            monthly_cash=monthly_cash,
            end_cash=end_cash,
            min_cash=min_cash,
            survives=min_cash >= 0,
            runway_months=round(runway, 1) if runway != float("inf") else 0.0,
        )

    async def advise(
        self,
        state: BusinessState,
        kpis: dict[str, Any],
        hurdle: HurdleEvent,
        chronicle: Chronicle,
    ) -> StrategistResult:
        options = await self.propose_options(state, kpis, hurdle, chronicle)
        projections = [
            self.project_option(state, option, hurdle) for option in options
        ]
        return StrategistResult(
            hurdle_id=hurdle.event_id,
            options=options,
            projections=projections,
        )
