"""Token budget enforcement for LLM report generation.

Two layers:

- **Per-report hard cap**: a Redis counter per report job (``cost_guard:report:<job>``)
  raised by the bridge's ``on_response`` hook; exceeding ``REPORT_TOKEN_LIMIT``
  raises ``CostLimitExceeded`` before the next LLM call.
- **Per-workspace monthly budget**: delegated to the existing metering service
  (``llm_tokens`` metric), so plan tiers and the billing usage page stay the
  single source of truth.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.exceptions import DomainError

logger = logging.getLogger("forge.cost_guard")

#: Hard cap per single report generation (tokens, input + output).
REPORT_TOKEN_LIMIT = 150_000

REDIS_PREFIX = "cost_guard:"


class CostLimitExceeded(DomainError):
    """Raised when a token budget would be exceeded before an LLM call."""

    def __init__(self, *, used: int, limit: int, scope: str) -> None:
        self.used = used
        self.limit = limit
        self.scope = scope
        super().__init__(
            status_code=429,
            detail=f"{scope} token budget exceeded: {used}/{limit} used",
        )


def _report_key(report_job_id: str) -> str:
    return f"{REDIS_PREFIX}report:{report_job_id}"


async def _redis() -> Redis:
    """Lazy Redis client for the report counters (tests pass their own)."""
    settings = get_settings()
    client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return client


async def get_report_usage(report_job_id: str, r: Redis | None = None) -> int:
    """Tokens already consumed by a report job (0 when Redis is unavailable)."""
    client = r or await _redis()
    try:
        raw = await client.get(_report_key(report_job_id))
        return int(raw) if raw else 0
    except Exception:  # noqa: BLE001 — best-effort accounting
        return 0
    finally:
        if r is None:
            await client.aclose()


async def record_report_usage(
    report_job_id: str, tokens: int, r: Redis | None = None
) -> None:
    """Accumulate a report job's token usage (1h expiry, best-effort)."""
    client = r or await _redis()
    try:
        await client.incrby(_report_key(report_job_id), tokens)
        await client.expire(_report_key(report_job_id), 3600)
    except Exception:  # noqa: BLE001 — best-effort accounting
        logger.warning("cost_guard: failed to record report usage", exc_info=True)
    finally:
        if r is None:
            await client.aclose()


async def check_report_budget(
    report_job_id: str, amount: int = 1, r: Redis | None = None
) -> None:
    """Raise ``CostLimitExceeded`` when the report would exceed its hard cap."""
    used = await get_report_usage(report_job_id, r)
    if used + amount > REPORT_TOKEN_LIMIT:
        raise CostLimitExceeded(
            used=used, limit=REPORT_TOKEN_LIMIT, scope="report"
        )


async def check_monthly_budget(
    db: Any, workspace_id: uuid.UUID | str, amount: int = 1
) -> None:
    """Raise ``PlanLimitExceeded`` when the workspace can't afford ``amount``.

    Delegates to the plan tier's ``llm_tokens_per_month`` limit.
    """
    from app.services import metering_service

    await metering_service.check_limit(db, workspace_id, "llm_tokens", amount=amount)


async def record_monthly_usage(
    db: Any, workspace_id: uuid.UUID | str, tokens: int
) -> None:
    """Increment the workspace's monthly LLM token meter."""
    from app.services import metering_service

    await metering_service.increment(db, workspace_id, "llm_tokens", amount=tokens)
