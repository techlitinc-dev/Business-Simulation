from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from app.agents import bridge
from app.core.config import get_settings
from app.core.exceptions import StructuredOutputError
from app.services.actuals.variance import VarianceDelta

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "variance_narrative.md").read_text(
    encoding="utf-8"
)


class VarianceNarrativeOutput(BaseModel):
    headline: str = Field(..., description="One-sentence summary of the change")
    explanation: str = Field(..., min_length=100, description="2-3 paragraph explanation")
    primary_driver: str = Field(..., description="The single most impactful factor")
    outlook: str = Field(..., description="1-sentence forward-looking statement")


def _build_prompt(delta: VarianceDelta) -> str:
    data = {
        "month": delta.month,
        "survival_rate_change": (
            f"{delta.prior_survival_rate:.0%} → {delta.new_survival_rate:.0%} "
            f"({delta.survival_delta:+.0%})"
        ),
        "runway_change": (
            f"{delta.prior_runway_median:.1f} → {delta.new_runway_median:.1f} "
            f"months ({delta.runway_delta:+.1f})"
        ),
        "resilience_score_change": (
            f"{delta.prior_resilience_score:.1f} → {delta.new_resilience_score:.1f} "
            f"({delta.score_delta:+.1f})"
        ),
        "key_changes": delta.key_changes,
    }
    return f"""You are a business analyst explaining simulation variance to a founder.

VARIANCE DATA:
{json.dumps(data, indent=2)}

RULES:
- headline: one sentence using exact numbers from the data above.
- explanation: 2-3 paragraphs explaining the variance. Reference the key_changes.
- primary_driver: the single most impactful change from key_changes.
- outlook: 1 forward-looking sentence.
- Do NOT invent numbers. Use only the values provided above.
"""


async def narrate_variance(delta: VarianceDelta) -> VarianceNarrativeOutput:
    """
    Call DeepSeek to generate a plain-English explanation of the variance delta.
    All numbers in the output are grounded in the delta object — no fabrication.
    Falls back to a deterministic summary when the LLM is unavailable.
    """
    from app.agents.llm.factory import get_llm_provider

    provider = get_llm_provider(get_settings())
    prompt = _build_prompt(delta)

    logger.info(
        "[variance_narrator] Generated narrative for blueprint %s month %s",
        delta.blueprint_id,
        delta.month,
    )

    try:
        result = await bridge.generate_structured(
            provider,
            VarianceNarrativeOutput,
            _SYSTEM_PROMPT,
            f"Explain this variance to the founder.\n\n{prompt}",
            temperature=0.2,
        )
    except StructuredOutputError:
        return _fallback_output(delta)
    return result


def _fallback_output(delta: VarianceDelta) -> VarianceNarrativeOutput:
    """Deterministic narrative from the delta alone (no LLM)."""
    driver = delta.key_changes[0] if delta.key_changes else "no single field moved"
    direction = "improved" if delta.survival_delta > 0 else "worsened"
    return VarianceNarrativeOutput(
        headline=(
            f"Survival {direction} from {delta.prior_survival_rate:.0%} to "
            f"{delta.new_survival_rate:.0%} (month {delta.month})."
        ),
        explanation=(
            f"After importing actuals through month {delta.month}, the re-baselined "
            f"forecast {direction}: survival went from {delta.prior_survival_rate:.0%} "
            f"to {delta.new_survival_rate:.0%} and median runway moved from "
            f"{delta.prior_runway_median:.1f} to {delta.new_runway_median:.1f} months. "
            f"Resilience score changed from {delta.prior_resilience_score:.1f} to "
            f"{delta.new_resilience_score:.1f}."
        ),
        primary_driver=driver,
        outlook=(
            "Keep monitoring the same fields next month to confirm the trend."
        ),
    )
