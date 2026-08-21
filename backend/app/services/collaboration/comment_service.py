"""Comment and approval business logic."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.models.comment import ApprovalRecord, Comment
from app.services.collaboration.schemas import (
    ApprovalDecision,
    ApprovalRequest,
    CommentCreate,
)

logger = logging.getLogger("forge.collaboration")


def _dispatch_mention_notifications(
    workspace_id: str, body: str, link: str, mentioned_ids: list[str]
) -> None:
    """Best-effort mention notifications.

    T37 wires a real notification service; until then, log the mentions so
    the hook is exercised without a broker dependency (matches alert_service).
    """
    for mentioned_id in mentioned_ids:
        try:
            from app.services.notification_service import (  # type: ignore[import-not-found]
                create_notification,
            )

            create_notification(
                workspace_id=workspace_id,
                user_id=mentioned_id,
                title="You were mentioned in a comment",
                body=body[:100],
                link=link,
                notification_type="mention",
            )
        except Exception:  # noqa: BLE001 — notification dispatch must never fail the comment
            logger.info(
                "[collab] mention notification skipped (T37 hook) user=%s ws=%s",
                mentioned_id,
                workspace_id,
            )


async def add_comment(
    data: CommentCreate, workspace_id: uuid.UUID, author_id: uuid.UUID, db: AsyncSession
) -> Comment:
    """Create a comment and dispatch mention notifications."""
    comment = Comment(
        workspace_id=workspace_id,
        author_user_id=author_id,
        target_type=data.target_type,
        target_id=data.target_id,
        section_ref=data.section_ref,
        body=data.body,
        mentions=",".join(data.mentions) if data.mentions else None,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    _dispatch_mention_notifications(
        workspace_id=str(workspace_id),
        body=data.body,
        link=f"/{data.target_type}/{data.target_id}",
        mentioned_ids=data.mentions,
    )
    return comment


async def get_comments(
    target_type: str, target_id: str, db: AsyncSession
) -> list[Comment]:
    """Return a target's comments, oldest first."""
    result = await db.execute(
        select(Comment)
        .where(Comment.target_type == target_type, Comment.target_id == target_id)
        .order_by(Comment.created_at)
    )
    return list(result.scalars().all())


async def submit_for_approval(
    req: ApprovalRequest, workspace_id: uuid.UUID, submitted_by: uuid.UUID, db: AsyncSession
) -> ApprovalRecord:
    """Open a pending approval record for a target."""
    record = ApprovalRecord(
        workspace_id=workspace_id,
        target_type=req.target_type,
        target_id=req.target_id,
        submitted_by=submitted_by,
        status="pending",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def decide_approval(
    approval_id: str, approver_id: uuid.UUID, decision: ApprovalDecision, db: AsyncSession
) -> ApprovalRecord:
    """Approve or reject a pending approval record."""
    record = await db.scalar(
        select(ApprovalRecord).where(ApprovalRecord.id == approval_id)
    )
    if record is None:
        raise DomainError(status_code=404, detail="Approval record not found")

    from datetime import UTC, datetime

    record.approved_by = approver_id
    record.status = decision.decision
    record.verdict_note = decision.note or None
    record.decided_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(record)
    return record
