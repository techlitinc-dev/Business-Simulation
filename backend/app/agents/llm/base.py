"""LLM provider abstraction: response model, Protocol, and MockProvider.

Every agent in the AI Cortex talks to this interface — never to ``openai``
directly (only ``openai_compat.py`` imports the SDK). The MockProvider is the
deterministic dev/test backend used whenever no API key is configured.

Unregistered prompts fall back to deterministic, schema-valid output for the
two known agent prompt shapes (hurdle generation, strategic options) so the
whole product works end-to-end with no API key; anything else gets ``{}``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

_CATEGORIES = ["market", "operational", "financial", "black_swan", "internal"]


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: float


class LLMProvider(Protocol):
    """Minimal interface every provider must implement."""

    model: str

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse: ...


def _hash_seed(*parts: str) -> int:
    """Deterministic 64-bit seed from prompt text (stable across processes)."""
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _pick(seed: int, options: list[str]) -> str:
    """Deterministic pick from a list."""
    return options[seed % len(options)]


def _mock_hurdle(user: str) -> str:
    """Build a deterministic, schema-valid Format B hurdle from the prompt hash."""
    seed = _hash_seed(user)
    actor = _pick(
        seed, ["Competitor X", "Regulator Y", "Supplier Z", "Investor A", "Key hire B"]
    )
    category = _pick(seed >> 4, _CATEGORIES)
    deltas = {
        "cac_delta_percent": (seed % 41) - 5,
        "churn_delta_percent": (seed >> 8) % 21,
        "new_signups_delta_percent": -((seed >> 12) % 41),
        "team_morale_delta": -round(((seed >> 16) % 21) / 100, 2),
        "cash_burn_delta_monthly": ((seed >> 20) % 9) * 1000,
        "mrr_delta_percent": ((seed >> 24) % 11) - 10,
    }
    return json.dumps(
        {
            "event_id": f"evt_{seed % 100000:05d}",
            "trigger_timing": f"Month {1 + seed % 12}",
            "category": category,
            "narrative": {
                "title": f"{actor} shakes the market",
                "story": (
                    f"{actor} makes a move that pressures the model. "
                    "The management team must respond."
                ),
                "source_actor": actor,
                "believability_score": round(0.6 + (seed % 40) / 100, 2),
            },
            "mechanical_impact": {
                "immediate": deltas,
                "cascading": {"month 2": "Impact persists for the quarter."},
            },
            "ai_game_master_note": "Respond decisively — the market is watching.",
        }
    )


def _mock_options(user: str) -> str:
    """Build a deterministic, schema-valid 3-option StrategicOptionList."""
    seed = _hash_seed(user)
    options = [
        {
            "option_id": "A",
            "name": "Defend the base",
            "description": "Reinforce the core offer and cut discretionary spend.",
            "cash_impact_monthly": -((seed % 9) + 2) * 1000,
            "probability_success": round(0.55 + (seed % 30) / 100, 2),
            "second_order_risk": "Growth slows in the next quarter.",
            "required_execution": "Trim spend, renegotiate vendor contracts.",
        },
        {
            "option_id": "B",
            "name": "Attack the gap",
            "description": "Push the new market angle aggressively.",
            "cash_impact_monthly": -((seed % 12) + 6) * 1000,
            "probability_success": round(0.35 + ((seed >> 8) % 25) / 100, 2),
            "second_order_risk": "Cash runway shortens materially.",
            "required_execution": "Launch the campaign within 30 days.",
        },
        {
            "option_id": "C",
            "name": "Hold and monitor",
            "description": "Make no big moves; watch the signals for a month.",
            "cash_impact_monthly": 0,
            "probability_success": round(0.45 + ((seed >> 12) % 20) / 100, 2),
            "second_order_risk": "The market may move faster than you do.",
            "required_execution": "Weekly war-room reviews.",
        },
    ]
    return json.dumps({"options": options})


class MockProvider:
    """Deterministic provider for dev/test. Identical prompts -> identical output.

    ``register(substring, response)`` pins exact canned output for any user
    prompt containing ``substring`` (first match wins). Unregistered prompts
    that ask for a hurdle or strategic options get deterministic valid output;
    anything else falls back to ``{}``.
    """

    def __init__(self, model: str = "mock-model") -> None:
        self.model = model
        self._registry: list[tuple[str, str]] = []

    def register(self, substring: str, response: str) -> None:
        self._registry.append((substring, response))

    def _canned(self, user: str) -> str:
        for substring, response in self._registry:
            if substring in user:
                return response
        if "Generate one context-aware hurdle" in user:
            return _mock_hurdle(user)
        if "Advise on this hurdle" in user:
            return _mock_options(user)
        return "{}"

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        content = self._canned(user)
        seed = _hash_seed(system, user, content)
        # Deterministic pseudo-values derived from the prompt hash — never random.
        prompt_tokens = seed % 400 + 100
        completion_tokens = (seed >> 16) % 400 + 50
        latency_ms = (seed >> 32) % 500 + 50
        return LLMResponse(
            content=content,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=0.0,
            latency_ms=float(latency_ms),
        )
