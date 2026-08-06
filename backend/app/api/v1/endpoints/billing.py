"""Billing endpoints (T40/T41)."""

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentWorkspace, DbSession
from app.core.exceptions import DomainError
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
    SubscriptionResponse,
    UsageResponse,
)
from app.services import billing_service
from app.services.metering_service import get_current_usage

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout")
async def checkout(
    payload: CheckoutRequest,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> CheckoutResponse:
    try:
        url = await billing_service.create_checkout_session(
            db, workspace=workspace, tier=payload.tier
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return CheckoutResponse(checkout_url=url)


@router.post("/portal")
async def portal(db: DbSession, workspace: CurrentWorkspace) -> PortalResponse:
    try:
        url = await billing_service.create_portal_session(db, workspace=workspace)
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return PortalResponse(portal_url=url)


@router.get("/subscription")
async def subscription(
    db: DbSession, workspace: CurrentWorkspace
) -> SubscriptionResponse:
    return await billing_service.get_subscription(db, workspace=workspace)


@router.get("/usage")
async def usage(db: DbSession, workspace: CurrentWorkspace) -> UsageResponse:
    record = await get_current_usage(db, workspace.id)
    from app.services.plans import get_plan

    plan = get_plan(workspace.plan_tier or "free")
    return UsageResponse(
        tier=workspace.plan_tier or "free",
        period=record.period,
        usage={
            "runs_used": record.runs_used,
            "mc_ticks_used": record.mc_ticks_used,
            "llm_tokens_used": record.llm_tokens_used,
        },
        limits={
            "runs_per_month": plan.runs_per_month,
            "monte_carlo_runs_per_batch": plan.monte_carlo_runs_per_batch,
            "llm_tokens_per_month": plan.llm_tokens_per_month,
            "seats": plan.seats,
        },
    )
