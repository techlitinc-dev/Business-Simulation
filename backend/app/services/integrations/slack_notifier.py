"""Slack notifier — sends messages to an incoming webhook URL.

Best-effort by design: delivery failures are logged, never raised, so
callers (run completion, drift alerts) are not affected by Slack outages.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("forge.integrations.slack")


async def send_slack_message(
    webhook_url: str, message: str, blocks: list[dict[str, Any]] | None = None
) -> None:
    """Send a message to a Slack incoming webhook URL (never raises)."""
    payload: dict[str, Any] = {"text": message}
    if blocks:
        payload["blocks"] = blocks
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload, timeout=5.0)
            resp.raise_for_status()
        logger.info("[slack] Message sent to webhook (status %s)", resp.status_code)
    except Exception as exc:  # noqa: BLE001 — delivery must never raise
        logger.warning("[slack] Failed to send message: %s", exc)


async def notify_run_complete(
    webhook_url: str, run_id: str, survival_rate: float, score: float
) -> None:
    """Post a run-completion summary to Slack."""
    message = (
        f"✅ *Simulation Complete* — Run `{run_id}`\n"
        f"Survival Rate: {survival_rate:.0%} | Resilience Score: {score:.1f}"
    )
    await send_slack_message(webhook_url, message)


async def notify_drift_alert(
    webhook_url: str, blueprint_id: str, score_delta: float
) -> None:
    """Post a drift alert to Slack."""
    message = (
        f"📉 *Drift Alert* — Blueprint `{blueprint_id}`\n"
        f"Resilience score dropped {abs(score_delta):.1f} points "
        "after latest actuals import."
    )
    await send_slack_message(webhook_url, message)
