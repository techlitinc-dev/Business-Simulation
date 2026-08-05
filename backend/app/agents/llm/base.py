"""LLM provider abstraction: response model, Protocol, and MockProvider.

Every agent in the AI Cortex talks to this interface — never to ``openai``
directly (only ``openai_compat.py`` imports the SDK). The MockProvider is the
deterministic dev/test backend used whenever no API key is configured.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol


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


class MockProvider:
    """Deterministic provider for dev/test. Identical prompts -> identical output.

    ``register(substring, response)`` pins exact canned output for any user
    prompt containing ``substring`` (first match wins). Unregistered prompts
    get a stable fallback JSON ``"{}"``.
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
