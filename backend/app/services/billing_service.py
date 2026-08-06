"""Stripe billing business logic (T40)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models.billing import Subscription
from app.models.workspace import Workspace
from app.schemas.billing import SubscriptionResponse
from app.services.plans import get_plan, get_plans

logger = logging.getLogger("forge.billing")

#: Stripe event types that carry subscription state we mirror into the DB.
_SUBSCRIPTION_EVENTS = {"customer.subscription.updated", "customer.subscription.created"}


def _stripe() -> Any:
    """Lazily import + configure the Stripe SDK (mocked in tests)."""
    import stripe

    settings = get_settings()
    if not settings.stripe_secret_key:
        raise DomainError(status_code=503, detail="Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key
    return stripe


def _price_id_for_tier(tier: str) -> str:
    plan = get_plan(tier)
    if plan.stripe_price_id is None:
        raise DomainError(status_code=422, detail=f"Tier '{tier}' has no Stripe price")
    return plan.stripe_price_id


async def _get_or_create_subscription(
    db: AsyncSession, workspace: Workspace
) -> Subscription:
    sub = await db.scalar(
        select(Subscription).where(Subscription.workspace_id == workspace.id)
    )
    if sub is None:
        sub = Subscription(
            workspace_id=workspace.id,
            tier="free",
            status="active",
        )
        db.add(sub)
        await db.flush()
    return sub


async def _ensure_stripe_customer(db: AsyncSession, workspace: Workspace) -> str:
    """Return the workspace's Stripe customer id, creating one if needed."""
    if workspace.stripe_customer_id:
        return workspace.stripe_customer_id

    stripe = _stripe()
    customer = stripe.Customer.create(email=None, metadata={"workspace_id": str(workspace.id)})
    workspace.stripe_customer_id = customer["id"]
    await db.commit()
    return str(customer["id"])


async def create_checkout_session(
    db: AsyncSession, *, workspace: Workspace, tier: str
) -> str:
    """Create a Stripe Checkout session for upgrading to ``tier``."""
    settings = get_settings()
    price_id = _price_id_for_tier(tier)
    customer_id = await _ensure_stripe_customer(db, workspace)

    stripe = _stripe()
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.frontend_url}/app/settings?checkout=success",
        cancel_url=f"{settings.frontend_url}/pricing",
        metadata={"workspace_id": str(workspace.id), "tier": tier},
    )
    return str(session["url"])


async def create_portal_session(db: AsyncSession, *, workspace: Workspace) -> str:
    """Open the Stripe customer portal (404 if no Stripe customer yet)."""
    if not workspace.stripe_customer_id:
        raise DomainError(status_code=404, detail="No Stripe customer for this workspace")

    stripe = _stripe()
    settings = get_settings()
    session = stripe.billing_portal.Session.create(
        customer=workspace.stripe_customer_id,
        return_url=f"{settings.frontend_url}/app/settings",
    )
    return str(session["url"])


async def get_subscription(
    db: AsyncSession, *, workspace: Workspace
) -> SubscriptionResponse:
    """Return the workspace's subscription (defaults to free)."""
    sub = await db.scalar(
        select(Subscription).where(Subscription.workspace_id == workspace.id)
    )
    if sub is None:
        return SubscriptionResponse(tier="free", status="active", current_period_end=None)
    return SubscriptionResponse.model_validate(sub)


async def handle_webhook_event(db: AsyncSession, event: dict[str, Any]) -> dict[str, Any]:
    """Mirror a Stripe subscription event into the Subscription table.

    Idempotent by event id: re-delivering the same event returns
    ``{"duplicate": True}`` without touching the row.
    """
    event_id = event.get("id", "")
    event_type = event.get("type", "")

    if event_type not in _SUBSCRIPTION_EVENTS:
        return {"received": event_type}

    data = event.get("data", {}).get("object", {})
    customer_id = data.get("customer")
    subscription_id = data.get("id")

    sub = await db.scalar(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
    )
    if sub is None:
        # New subscription — find the workspace by Stripe customer id.
        workspace = await db.scalar(
            select(Workspace).where(Workspace.stripe_customer_id == customer_id)
        )
        if workspace is None:
            logger.warning("stripe webhook: unknown customer %s", customer_id)
            return {"received": event_type, "ignored": "unknown_customer"}
        sub = Subscription(
            workspace_id=workspace.id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            tier="free",
            status="active",
        )
        db.add(sub)
        created = True
    else:
        created = False

    # Idempotency: a re-delivered event id is a no-op.
    if event_id in (sub.processed_event_ids or []):
        return {"received": event_type, "duplicate": True}

    # Mirror the Stripe payload: status, period end, and tier.
    sub.status = data.get("status", sub.status)
    sub.current_period_end = _period_end(data)

    item = (data.get("items") or {}).get("data") or []
    price_id = None
    if item:
        price_id = (item[0].get("price") or {}).get("id")
    tier = _tier_from_price(price_id)
    if tier is not None:
        sub.tier = tier

    workspace = await db.get(Workspace, sub.workspace_id)
    if workspace is not None:
        workspace.plan_tier = sub.tier

    processed = list(sub.processed_event_ids or [])
    processed.append(event_id)
    sub.processed_event_ids = processed[-1000:]

    await db.commit()
    if created:
        return {"received": event_type, "created": True}
    return {"received": event_type, "updated": True}


def _period_end(data: dict[str, Any]) -> datetime | None:
    ts = data.get("current_period_end")
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=UTC)


def _tier_from_price(price_id: str | None) -> str | None:
    if not price_id:
        return None
    for plan in get_plans().values():
        if plan.stripe_price_id == price_id:
            return plan.id
    return None
