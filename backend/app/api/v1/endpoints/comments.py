"""Comment + approval endpoints (workspace-scoped)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.services.collaboration.comment_service import (
    add_comment,
    decide_approval,
    get_comments,
    submit_for_approval,
)
from app.services.collaboration.schemas import (
    ApprovalDecision,
    ApprovalOut,
    ApprovalRequest,
    CommentCreate,
    CommentOut,
)

router = APIRouter(prefix="/comments", tags=["comments"])


@router.post("", status_code=201, response_model=CommentOut)
async def post_comment(
    body: CommentCreate,
    db: DbSession,
    user: CurrentUser,
    workspace: CurrentWorkspace,
) -> CommentOut:
    comment = await add_comment(body, workspace.id, user.id, db)
    return CommentOut.model_validate(comment)


@router.get("/{target_type}/{target_id}", response_model=list[CommentOut])
async def list_comments(
    target_type: str, target_id: str, db: DbSession, workspace: CurrentWorkspace
) -> list[CommentOut]:
    comments = await get_comments(target_type, target_id, db)
    return [CommentOut.model_validate(c) for c in comments]


@router.post("/approvals", status_code=201, response_model=ApprovalOut)
async def submit_approval(
    body: ApprovalRequest,
    db: DbSession,
    user: CurrentUser,
    workspace: CurrentWorkspace,
) -> ApprovalOut:
    record = await submit_for_approval(body, workspace.id, user.id, db)
    return ApprovalOut.model_validate(record)


@router.post("/approvals/{approval_id}/decide", response_model=ApprovalOut)
async def decide(
    approval_id: str,
    body: ApprovalDecision,
    db: DbSession,
    user: CurrentUser,
) -> ApprovalOut:
    record = await decide_approval(approval_id, user.id, body, db)
    return ApprovalOut.model_validate(record)
