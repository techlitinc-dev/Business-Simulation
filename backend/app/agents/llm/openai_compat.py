"""OpenAI-compatible provider (DeepSeek, vLLM, Ollama, ...) with retries.

This is the ONLY module under ``app/agents/`` allowed to import ``openai``.
Retries cover timeout, rate-limit, connection, and 5xx errors with plain
exponential backoff (1s, 2s, 4s, ... capped at 10s) — no retry dependency.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import openai
from openai import AsyncOpenAI

from app.agents.llm.base import LLMResponse

_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APIStatusError,
)

_MAX_BACKOFF_SECONDS = 10.0


class OpenAICompatibleProvider:
    def __init__(self, settings: Any) -> None:
        self.model = settings.llm_model
        self._timeout = settings.llm_timeout_seconds
        self._max_retries = settings.llm_max_retries
        self._input_price = settings.llm_cost_per_1k_input_tokens
        self._output_price = settings.llm_cost_per_1k_output_tokens
        self._client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

    def _cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return float(
            prompt_tokens / 1000 * self._input_price
            + completion_tokens / 1000 * self._output_price
        )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, _RETRYABLE_EXCEPTIONS):
            # 4xx status errors (bad request, auth) are not retryable.
            if isinstance(exc, openai.APIStatusError):
                return exc.status_code >= 500
            return True
        return False

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        last_exc: Exception | None = None
        start = time.monotonic()
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self._timeout,
                )
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                return LLMResponse(
                    content=response.choices[0].message.content or "",
                    model=self.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=self._cost(prompt_tokens, completion_tokens),
                    latency_ms=(time.monotonic() - start) * 1000,
                )
            except Exception as exc:  # noqa: BLE001 — re-raised after retries
                last_exc = exc
                if not self._is_retryable(exc) or attempt >= self._max_retries:
                    raise
                backoff = min(2**attempt, _MAX_BACKOFF_SECONDS)
                await asyncio.sleep(backoff)

        assert last_exc is not None
        raise last_exc
