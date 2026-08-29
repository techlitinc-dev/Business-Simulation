"""Token budget enforcement for LLM report generation.

Three layers:

- **Per-report hard cap**: a Redis counter per report job (``cost_guard:report:<job>``)
  raised by the bridge's ``on_response`` hook; exceeding ``REPORT_TOKEN_LIMIT``
  raises ``CostLimitExceeded`` (HTTP 429) before the next LLM call.
- **Per-workspace monthly budget**: a Redis counter per workspace
  (``cost_guard:monthly:<workspace_id>``, 35-day expiry) incremented by
  ``record_usage``; exceeding ``MONTHLY_TOKEN_LIMIT`` raises ``CostLimitExceeded``
  (HTTP 429).
- **Plan-tier metering**: ``check_monthly_budget``/``record_monthly_usage`` also
  delegate to the existing metering service (``llm_tokens`` metric) so plan tiers
  and the billing usage page stay the single source of truth for paywalls.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, cast

import redis as redis_lib
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.exceptions import DomainError

logger = logging.getLogger("forge.cost_guard")

#: Hard cap per single report generation (tokens, input + output).
REPORT_TOKEN_LIMIT = 150_000
#: Hard cap per workspace per month (tokens).
MONTHLY_TOKEN_LIMIT = 2_000_000

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


def _get_redis() -> redis_lib.Redis:
    """Sync Redis client for the monthly budget counters (Day 32 spec).

    Used by the mock-patchable ``get_monthly_usage``/``record_usage``/``check_monthly_budget``
    path; tests patch this symbol so no real Redis is needed.
    """
    settings = get_settings()
    return cast(redis_lib.Redis, redis_lib.from_url(settings.redis_url))  # type: ignore[no-untyped-call]


def _monthly_key(workspace_id: str) -> str:
    return f"{REDIS_PREFIX}monthly:{workspace_id}"


def get_monthly_usage(workspace_id: str) -> int:
    """Tokens a workspace has consumed this month (0 when Redis is down)."""
    r = _get_redis()
    try:
        raw = r.get(_monthly_key(workspace_id))
        return int(str(raw)) if raw else 0
    except Exception:  # noqa: BLE001 — best-effort accounting
        return 0
    finally:
        r.close()


def record_usage(
    workspace_id: str, tokens: int, report_job_id: str | None = None
) -> None:
    """Accumulate a workspace's monthly token usage (35-day expiry).

    Also bumps the per-report counter when ``report_job_id`` is given (1h expiry).
    """
    r = _get_redis()
    try:
        r.incrby(_monthly_key(workspace_id), tokens)
        r.expire(_monthly_key(workspace_id), 60 * 60 * 24 * 35)
        if report_job_id:
            r.incrby(_report_key(report_job_id), tokens)
            r.expire(_report_key(report_job_id), 3600)
    except Exception:  # noqa: BLE001 — best-effort accounting
        logger.warning("cost_guard: failed to record usage", exc_info=True)
    finally:
        r.close()


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
    workspace_id: uuid.UUID | str, db: Any | None = None, amount: int = 1
) -> None:
    """Raise ``CostLimitExceeded`` (429) when the monthly Redis budget is spent.

    When a ``db`` session is supplied, also delegate to the plan tier's
    ``llm_tokens_per_month`` limit via the metering service (raises
    ``PlanLimitExceeded`` → 402 for paywalls).
    """
    used = get_monthly_usage(str(workspace_id))
    if used + amount > MONTHLY_TOKEN_LIMIT:
        raise CostLimitExceeded(
            used=used, limit=MONTHLY_TOKEN_LIMIT, scope="monthly"
        )

    if db is None:
        return
    from app.services import metering_service

    await metering_service.check_limit(db, workspace_id, "llm_tokens", amount=amount)


async def record_monthly_usage(
    db: Any, workspace_id: uuid.UUID | str, tokens: int
) -> None:
    """Increment the workspace's monthly LLM token meter."""
    record_usage(str(workspace_id), tokens)
    from app.services import metering_service

    await metering_service.increment(db, workspace_id, "llm_tokens", amount=tokens)
