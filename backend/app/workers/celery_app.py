"""Celery application for background jobs (Monte Carlo runs, email)."""

from collections.abc import Callable
from typing import Any

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

# Fail fast when Redis is unreachable so `.delay()` doesn't hang for ~20s in
# dev/test — the endpoint callers guard the enqueue and log a fallback.
celery_app = Celery(
    "forge",
    broker=settings.redis_url,
    backend=settings.redis_url,
    broker_connection_retry_on_startup=False,
    broker_connection_timeout=1,
    broker_transport_options={"socket_timeout": 1, "socket_connect_timeout": 1},
)


def _task(name: str) -> Callable[[Callable[..., Any]], Any]:
    # Celery's untyped decorator returns Any; cast keeps mypy quiet.
    return celery_app.task(name=name)  # type: ignore[no-any-return]


@_task("forge.ping")
def ping() -> str:
    return "pong"
