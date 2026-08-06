"""Hurdle generator — vital signs -> Format B hurdle JSON (spec §6 Steps 1-3)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.agents import bridge
from app.agents.chronicle import Chronicle, ChronicleEntry
from app.agents.llm.base import LLMProvider
from app.engine.state import BusinessState
from app.schemas.hurdle import HurdleEvent

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "hurdle_generation.md").read_text(
    encoding="utf-8"
)


def build_vital_signs(state: BusinessState, kpis: dict[str, Any]) -> dict[str, Any]:
    """Produce the spec §6 Step 1 vital-signs snapshot from engine state."""
    fin = state.financials
    streams = state.streams
    first = streams[0] if streams else None

    # Revenue concentration across streams (top client % is approximated from
    # stream share — per-client detail is not tracked by the engine).
    total_revenue = sum(s.price_point * s.projected_customers_month_12 for s in streams)
    top_share = 0.0
    if total_revenue > 0 and streams:
        top = max(s.price_point * s.projected_customers_month_12 for s in streams)
        top_share = top / total_revenue

    cash_reserves = fin.cash
    burn = fin.monthly_burn
    runway = cash_reserves / burn if burn > 0 else float("inf")

    return {
        "burn_rate": round(burn, 2),
        "runway_months": round(runway, 1) if runway != float("inf") else None,
        "cash_reserves": round(cash_reserves, 2),
        "revenue_concentration": {
            "top_client_percent": round(top_share * 100, 1),
            "top_3_clients_percent": round(top_share * 100, 1),
        },
        "cac": first.cac if first else 0,
        "ltv": first.ltv if first else 0,
        "churn_monthly": first.churn_monthly if first else 0,
        "mrr": round(fin.mrr, 2),
        "month": state.month,
        "organic_acquisition": bool(kpis.get("organic_acquisition", False)),
    }


class HurdleGenerator:
    def __init__(
        self,
        provider: LLMProvider,
        on_response: Callable[[Any], Any] | None = None,
    ) -> None:
        self._provider = provider
        self._on_response = on_response

    async def generate(
        self,
        state: BusinessState,
        kpis: dict[str, Any],
        chronicle: Chronicle,
        *,
        difficulty: int = 1,
        month: int,
    ) -> HurdleEvent:
        vital = build_vital_signs(state, kpis)
        user_prompt = (
            "Generate one context-aware hurdle for the current simulation state.\n\n"
            f"VITAL SIGNS:\n{json.dumps(vital, indent=2)}\n\n"
            f"SIMULATION CHRONICLE:\n{chronicle.to_prompt_summary()}\n\n"
            f"CURRENT MONTH: {month}\n"
            f"DIFFICULTY: {difficulty} (1-3 standard, 4-10 compounding, 10+ nightmare)\n\n"
            "Output ONLY the Format B hurdle JSON described in your instructions."
        )
        hurdle = await bridge.generate_structured(
            self._provider,
            HurdleEvent,
            _SYSTEM_PROMPT,
            user_prompt,
            temperature=0.7,
            clamp=True,
            on_response=self._on_response,
        )

        # Continuity: record the hurdle in the chronicle automatically.
        chronicle.add_entry(
            ChronicleEntry(
                month=month,
                event_id=hurdle.event_id,
                title=hurdle.narrative.title,
                actors=[hurdle.narrative.source_actor],
                summary=hurdle.narrative.story[:200],
            )
        )
        return hurdle
