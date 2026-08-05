"""Provider abstraction tests (T20): mock determinism, registry, factory, retries, cost."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import openai
import pytest
from app.agents.llm.base import MockProvider, _hash_seed
from app.agents.llm.factory import get_llm_provider
from app.agents.llm.openai_compat import OpenAICompatibleProvider

# --- MockProvider determinism + registry -------------------------------------


async def test_mock_deterministic() -> None:
    provider = MockProvider()
    a = await provider.complete("sys", "user prompt")
    b = await provider.complete("sys", "user prompt")
    assert a.content == b.content
    assert a.prompt_tokens == b.prompt_tokens
    assert a.completion_tokens == b.completion_tokens
    assert a.cost_usd == 0.0


async def test_mock_different_prompts_differ() -> None:
    provider = MockProvider()
    a = await provider.complete("sys", "hello")
    b = await provider.complete("sys", "world")
    assert a.content != b.content or a.prompt_tokens != b.prompt_tokens


async def test_mock_registry_first_match_wins() -> None:
    provider = MockProvider()
    provider.register("runway", '{"a": 1}')
    provider.register("runway is low", '{"b": 2}')
    resp = await provider.complete("sys", "the runway is low today")
    assert resp.content == '{"a": 1}'
    # fallback for unregistered prompt
    resp2 = await provider.complete("sys", "something else")
    assert resp2.content == "{}"


async def test_mock_seed_is_stable() -> None:
    assert _hash_seed("a", "b") == _hash_seed("a", "b")
    assert _hash_seed("a", "b") != _hash_seed("a", "c")


# --- Factory selection -------------------------------------------------------


def test_factory_mock_when_no_key() -> None:
    settings = SimpleNamespace(
        llm_provider="auto", llm_api_key=None, llm_model="m", llm_base_url=""
    )
    provider = get_llm_provider(settings)
    assert isinstance(provider, MockProvider)


def test_factory_openai_when_key_set() -> None:
    settings = SimpleNamespace(
        llm_provider="auto",
        llm_api_key="sk-test",
        llm_model="m",
        llm_base_url="https://example.com",
    )
    with patch("app.agents.llm.factory.OpenAICompatibleProvider") as cls:
        get_llm_provider(settings)
        cls.assert_called_once()


def test_factory_mock_forced_with_key() -> None:
    settings = SimpleNamespace(
        llm_provider="mock", llm_api_key="sk-test", llm_model="m", llm_base_url=""
    )
    provider = get_llm_provider(settings)
    assert isinstance(provider, MockProvider)


# --- OpenAICompatibleProvider retries + cost ---------------------------------


def _settings(**overrides):
    base = dict(
        llm_model="m",
        llm_base_url="https://example.com",
        llm_api_key="sk-test",
        llm_timeout_seconds=60.0,
        llm_max_retries=3,
        llm_cost_per_1k_input_tokens=0.0,
        llm_cost_per_1k_output_tokens=0.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _usage(prompt: int, completion: int):
    return SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion)


def _ok_response(content: str = "hi", usage=None):
    choice = SimpleNamespace(message=SimpleNamespace(content=content))
    return SimpleNamespace(choices=[choice], usage=usage or _usage(100, 50))


async def test_openai_cost_formula() -> None:
    settings = _settings(
        llm_cost_per_1k_input_tokens=1.0, llm_cost_per_1k_output_tokens=2.0
    )
    provider = OpenAICompatibleProvider(settings)
    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=_ok_response())
    ) as create:
        resp = await provider.complete("s", "u")
    assert resp.prompt_tokens == 100
    assert resp.completion_tokens == 50
    assert resp.cost_usd == pytest.approx(100 / 1000 * 1.0 + 50 / 1000 * 2.0)
    create.assert_awaited_once()


async def test_openai_cost_zero_when_unpriced() -> None:
    provider = OpenAICompatibleProvider(_settings())
    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=_ok_response())
    ):
        resp = await provider.complete("s", "u")
    assert resp.cost_usd == 0.0


async def test_openai_retries_then_succeeds() -> None:
    """A transient APIStatusError (5xx) twice, then success -> 3 calls total."""
    provider = OpenAICompatibleProvider(_settings(llm_max_retries=3))

    fail = openai_api_error(500)
    mock_create = AsyncMock(side_effect=[fail, fail, _ok_response()])
    with (
        patch.object(provider._client.chat.completions, "create", mock_create),
        patch("app.agents.llm.openai_compat.asyncio.sleep", new=AsyncMock()),
    ):
        resp = await provider.complete("s", "u")

    assert resp.content == "hi"
    assert mock_create.await_count == 3


async def test_openai_retries_exhausted_raises() -> None:
    provider = OpenAICompatibleProvider(_settings(llm_max_retries=2))
    fail = openai_api_error(500)
    mock_create = AsyncMock(side_effect=fail)
    with (
        patch.object(provider._client.chat.completions, "create", mock_create),
        patch("app.agents.llm.openai_compat.asyncio.sleep", new=AsyncMock()),
        pytest.raises(openai.APIStatusError),
    ):
        await provider.complete("s", "u")
    # initial + 2 retries = 3 attempts
    assert mock_create.await_count == 3


async def test_openai_non_retryable_4xx_does_not_retry() -> None:
    provider = OpenAICompatibleProvider(_settings(llm_max_retries=3))
    mock_create = AsyncMock(side_effect=openai_api_error(400))
    with (
        patch.object(provider._client.chat.completions, "create", mock_create),
        pytest.raises(openai.APIStatusError),
    ):
        await provider.complete("s", "u")
    assert mock_create.await_count == 1


def openai_api_error(status: int):
    import httpx
    import openai

    request = httpx.Request("POST", "https://example.com/chat")
    response = httpx.Response(status_code=status, request=request)
    return openai.APIStatusError(
        message="boom",
        response=response,
        body=None,
    )
