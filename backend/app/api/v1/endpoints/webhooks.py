"""Stripe webhook endpoint (T40) — signature-verified, idempotent."""

import logging

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.deps import DbSession
from app.core.config import get_settings
from app.services import billing_service

logger = logging.getLogger("forge.webhooks")

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, object]:
    """Verify the Stripe signature and process the event idempotently."""
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhooks not configured")

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    import stripe

    try:
        payload_bytes = await request.body()
        event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload_bytes, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload") from None
    except stripe.error.SignatureVerificationError:  # type: ignore[attr-defined]
        raise HTTPException(status_code=400, detail="Invalid signature") from None

    return await billing_service.handle_webhook_event(db, event)
