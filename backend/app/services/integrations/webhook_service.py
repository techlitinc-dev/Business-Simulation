"""Outbound webhook dispatch — signed POSTs to registered endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_registration import WebhookRegistration

logger = logging.getLogger("forge.integrations.webhook")

_SIGNATURE_HEADER = "X-Forge-Signature"
_EVENT_HEADER = "X-Forge-Event"


def _sign_payload(payload: dict[str, Any], secret: str) -> str:
    """HMAC-SHA256 signature over the canonical (sorted-key) JSON body."""
    body = json.dumps(payload, sort_keys=True)
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


async def fire_webhook(
    target_url: str, event: str, payload: dict[str, Any], secret: str
) -> None:
    """Send a signed webhook POST to target_url (never raises)."""
    signature = _sign_payload(payload, secret)
    headers = {
        "Content-Type": "application/json",
        _EVENT_HEADER: event,
        f"{_SIGNATURE_HEADER}": f"sha256={signature}",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(target_url, json=payload, headers=headers, timeout=5.0)
        logger.info(
            "[webhook] %s → %s (%s)", event, target_url, resp.status_code
        )
    except Exception as exc:  # noqa: BLE001 — delivery must never raise
        logger.warning("[webhook] Failed to deliver %s: %s", event, exc)


async def dispatch_event(
    workspace_id: uuid.UUID, event: str, payload: dict[str, Any], db: AsyncSession
) -> None:
    """Dispatch an event to every active registration subscribed to it."""
    result = await db.execute(
        select(WebhookRegistration).where(
            WebhookRegistration.workspace_id == workspace_id,
            WebhookRegistration.active.is_(True),
        )
    )
    webhooks = result.scalars().all()
    for wh in webhooks:
        if event in wh.events:
            await fire_webhook(wh.target_url, event, payload, wh.secret)
