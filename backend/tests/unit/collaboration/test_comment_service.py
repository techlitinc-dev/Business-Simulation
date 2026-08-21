"""Unit tests for the collaboration comment service."""

from __future__ import annotations

import uuid

from app.db.session import async_session_factory
from app.models.comment import ApprovalRecord
from app.services.collaboration.comment_service import (
    add_comment,
    decide_approval,
    get_comments,
    submit_for_approval,
)
from app.services.collaboration.schemas import ApprovalDecision, ApprovalRequest, CommentCreate


async def test_add_comment_creates_record() -> None:
    async with async_session_factory() as db:
        data = CommentCreate(
            target_type="blueprint", target_id="bp_001", body="Looks good!"
        )
        comment = await add_comment(
            data, uuid.uuid4(), uuid.uuid4(), db
        )
        assert comment.body == "Looks good!"
        assert comment.mentions is None
        assert comment.id.startswith("cmt_")


async def test_add_comment_with_mentions() -> None:
    async with async_session_factory() as db:
        data = CommentCreate(
            target_type="run",
            target_id="run_001",
            body="@alice check this",
            mentions=["alice"],
        )
        comment = await add_comment(data, uuid.uuid4(), uuid.uuid4(), db)
        assert "alice" in (comment.mentions or "")


async def test_get_comments_returns_oldest_first() -> None:
    async with async_session_factory() as db:
        ws_id = uuid.uuid4()
        author = uuid.uuid4()
        await add_comment(
            CommentCreate(target_type="report", target_id="rep_1", body="first"),
            ws_id,
            author,
            db,
        )
        await add_comment(
            CommentCreate(target_type="report", target_id="rep_1", body="second"),
            ws_id,
            author,
            db,
        )
        comments = await get_comments("report", "rep_1", db)
        assert [c.body for c in comments] == ["first", "second"]
        # Other targets stay isolated.
        assert await get_comments("report", "rep_2", db) == []


async def test_submit_and_decide_approval() -> None:
    async with async_session_factory() as db:
        ws_id = uuid.uuid4()
        submitter = uuid.uuid4()
        approver = uuid.uuid4()

        record = await submit_for_approval(
            ApprovalRequest(target_type="blueprint", target_id="bp_001"),
            ws_id,
            submitter,
            db,
        )
        assert record.status == "pending"
        assert record.id.startswith("apr_")

        decided = await decide_approval(
            record.id,
            approver,
            ApprovalDecision(decision="approved", note="Ship it"),
            db,
        )
        assert decided.status == "approved"
        assert decided.approved_by == approver
        assert decided.verdict_note == "Ship it"
        assert decided.decided_at is not None
        assert isinstance(decided, ApprovalRecord)
