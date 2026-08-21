"""Webhook registration business logic."""

from __future__ import annotations

import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.models.webhook_registration import WebhookRegistration
from app.schemas.webhook import WebhookCreate, WebhookCreatedResponse


def _generate_secret() -> str:
    return secrets.token_urlsafe(32)


async def create_webhook(
    db: AsyncSession, *, workspace_id: uuid.UUID, data: WebhookCreate
) -> WebhookCreatedResponse:
    """Register an outbound webhook; returns the plaintext secret once."""
    secret = _generate_secret()
    registration = WebhookRegistration(
        workspace_id=workspace_id,
        name=data.name.strip(),
        target_url=data.target_url.strip(),
        events=list(data.events),
        secret=secret,
        active=True,
    )
    db.add(registration)
    await db.commit()
    await db.refresh(registration)
    return WebhookCreatedResponse(
        id=registration.id,
        name=registration.name,
        target_url=registration.target_url,
        events=registration.events,
        secret=secret,
    )


async def list_webhooks(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> list[WebhookRegistration]:
    result = await db.execute(
        select(WebhookRegistration)
        .where(WebhookRegistration.workspace_id == workspace_id)
        .order_by(WebhookRegistration.created_at)
    )
    return list(result.scalars().all())


async def delete_webhook(
    db: AsyncSession, *, workspace_id: uuid.UUID, webhook_id: str
) -> None:
    """Delete a registration scoped to the workspace (404 on any miss)."""
    registration = await db.scalar(
        select(WebhookRegistration).where(
            WebhookRegistration.id == webhook_id,
            WebhookRegistration.workspace_id == workspace_id,
        )
    )
    if registration is None:
        raise DomainError(status_code=404, detail="Webhook not found")
    await db.delete(registration)
    await db.commit()
