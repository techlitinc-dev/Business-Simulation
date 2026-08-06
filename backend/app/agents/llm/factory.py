"""Provider factory — picks MockProvider or OpenAICompatibleProvider from settings."""

from __future__ import annotations

from typing import Any

from app.agents.llm.base import LLMProvider, MockProvider
from app.agents.llm.openai_compat import OpenAICompatibleProvider


def get_llm_provider(settings: Any) -> LLMProvider:
    """Return a provider based on env config.

    - ``LLM_PROVIDER=mock`` forces the deterministic mock (even with a key set).
    - Otherwise auto: mock when no API key, OpenAI-compatible when a key exists.
    """
    if settings.llm_provider == "mock" or not settings.llm_api_key:
        return MockProvider(model=settings.llm_model)
    return OpenAICompatibleProvider(settings)


def provider_is_mock(provider: LLMProvider) -> bool:
    """True when the provider is the deterministic mock (dev/test mode)."""
    return isinstance(provider, MockProvider)
