"""Post-mortem agent — AI narrative for Format C (T31).

The LLM writes narrative text only; every figure in the optimization table
comes from the engine's ``estimate_survival_delta``. Invalid LLM output
triggers the bridge repair-retry, and a deterministic fallback table built
from the engine deltas keeps the report flowing without an API key.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agents import bridge
from app.agents.llm.base import LLMProvider
from app.core.exceptions import StructuredOutputError
from app.schemas.report import PostMortemOutput, SurvivalMetrics, TweakResult

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "post_mortem.md").read_text(
    encoding="utf-8"
)


def build_post_mortem_prompt(
    metrics: SurvivalMetrics,
    deltas: list[TweakResult],
    blueprint: dict[str, Any],
) -> str:
    return (
        "Write the post-mortem for this simulation run.\n\n"
        f"METRICS:\n{json.dumps(metrics.model_dump(mode='json'), indent=2)}\n\n"
        "ENGINE-MEASURED TWEAK DELTAS (survival rate, percentage points):\n"
        f"{json.dumps([d.model_dump(mode='json') for d in deltas], indent=2)}\n\n"
        f"BLUEPRINT:\n{json.dumps(blueprint, indent=2)[:4000]}\n\n"
        "Output ONLY the PostMortemOutput JSON described in your instructions. "
        "NEVER invent figures — reference only the numbers provided."
    )


def _fallback_output(deltas: list[TweakResult]) -> PostMortemOutput:
    """Deterministic table built from engine deltas alone (no LLM)."""
    best = max(deltas, key=lambda d: d.delta_pp) if deltas else None
    return PostMortemOutput(
        optimizations=[
            {
                "tweak_key": d.tweak_key,
                "recommendation": (
                    f"Apply '{d.label}' — engine re-runs show a "
                    f"{d.delta_pp:+.1f}pp survival impact."
                ),
                "implementation_cost": "Medium",
                "trade_off": "See counter-factual deltas above.",
            }
            for d in sorted(deltas, key=lambda d: -d.delta_pp)[:3]
        ],
        counter_factual_insight=(
            f"Engine re-runs rank '{best.label}' as the highest-impact "
            "optimization when no AI narrative is available."
            if best
            else "No optimization deltas were measurable."
        ),
        blueprint_v2_suggestions=[
            "Focus the next blueprint version on the top-ranked tweak.",
        ],
    )


class PostMortemAgent:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def generate(
        self,
        metrics: SurvivalMetrics,
        deltas: list[TweakResult],
        blueprint: dict[str, Any],
    ) -> PostMortemOutput:
        """Generate the AI narrative; fall back to engine-only output on error."""
        user_prompt = build_post_mortem_prompt(metrics, deltas, blueprint)
        try:
            output = await bridge.generate_structured(
                self._provider,
                PostMortemOutput,
                _SYSTEM_PROMPT,
                user_prompt,
                temperature=0.5,
            )
        except StructuredOutputError:
            return _fallback_output(deltas)
        return output
