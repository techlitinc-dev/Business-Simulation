from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Membership, Role
from app.services.actuals.variance import VarianceDelta
from app.services.workspace_service import get_workspace
from app.utils.email import get_email_backend

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 5.0  # pp drop in resilience score


async def should_alert(delta: VarianceDelta, threshold: float = DEFAULT_THRESHOLD) -> bool:
    return delta.score_delta <= -threshold


async def _owner_email(db: AsyncSession, workspace_id: uuid.UUID) -> str | None:
    """Email of the workspace owner (via the OWNER membership), if any."""
    from app.models.user import User

    result = await db.execute(
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.workspace_id == workspace_id,
            Membership.role == Role.OWNER,
        )
    )
    owner = result.scalars().first()
    return owner.email if owner is not None else None


async def dispatch_drift_alert(
    delta: VarianceDelta,
    workspace_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Send notification + email when resilience score drops past threshold."""
    workspace = await get_workspace(db, workspace_id=workspace_id)

    message = (
        f"Drift Alert: Your resilience score dropped {abs(delta.score_delta):.1f} points "
        f"(from {delta.prior_resilience_score:.1f} to {delta.new_resilience_score:.1f}) "
        f"after importing Month {delta.month} actuals. "
        f"Primary driver: {delta.key_changes[0] if delta.key_changes else 'unknown'}."
    )
    link = f"/blueprints/{delta.blueprint_id}/actuals"

    # Notification center (T37) — not built yet; log and continue.
    try:
        # TODO(T37): create_notification(db=db, workspace_id=..., title=...,
        #            body=message, link=link, notification_type="drift_alert")
        logger.info(
            "drift alert notification (T37 hook) workspace=%s blueprint=%s body=%s",
            str(workspace_id),
            delta.blueprint_id,
            message,
        )
    except Exception as exc:  # noqa: BLE001 - alerts must never raise
        logger.warning("drift alert notification failed: %s", exc)

    # Email the workspace owner (best-effort; console backend in dev).
    try:
        owner_email = await _owner_email(db, workspace_id)
        if owner_email:
            await get_email_backend().send(
                to=owner_email,
                subject=f"[Forge] Drift Alert — {workspace.name}",
                body_text=message + f"\n\nView full report: {link}",
            )
    except Exception as exc:  # noqa: BLE001 - alerts must never raise
        logger.warning("drift alert email failed: %s", exc)

    logger.info("drift alert dispatched blueprint=%s", delta.blueprint_id)
