# Day 29 — F-08: Comments, Annotations + Review Workflow

## Feature
F-08: Collaboration & Workflow

## Goal
Implement a polymorphic Comment model for blueprints/runs/reports/sections. Add an approval workflow (submit/approve/reject) and a read-only Guest role for investor access.

---

## Step 1 — Comment Model

`backend/app/models/comment.py`:
```python
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class Comment(Base):
    __tablename__ = "comments"
    id = Column(String, primary_key=True, default=lambda: f"cmt_{uuid.uuid4().hex[:12]}")
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    author_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    # Polymorphic target
    target_type = Column(String, nullable=False)    # "blueprint" | "run" | "report" | "section"
    target_id = Column(String, nullable=False, index=True)
    section_ref = Column(String, nullable=True)     # for report section annotations
    body = Column(Text, nullable=False)
    mentions = Column(String, nullable=True)        # comma-separated user_ids
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ApprovalRecord(Base):
    __tablename__ = "approval_records"
    id = Column(String, primary_key=True, default=lambda: f"apr_{uuid.uuid4().hex[:12]}")
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False, index=True)
    submitted_by = Column(String, ForeignKey("users.id"), nullable=False)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending")     # "pending" | "approved" | "rejected"
    verdict_note = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    decided_at = Column(DateTime(timezone=True), nullable=True)
```

---

## Step 2 — Comment & Approval Service

`backend/app/services/collaboration/comment_service.py`:
```python
from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.comment import Comment, ApprovalRecord
from pydantic import BaseModel
from datetime import datetime
import uuid


class CommentCreate(BaseModel):
    target_type: str
    target_id: str
    body: str
    mentions: list[str] = []
    section_ref: str | None = None


async def add_comment(data: CommentCreate, workspace_id: str, author_id: str, db: AsyncSession) -> Comment:
    comment = Comment(
        workspace_id=workspace_id, author_user_id=author_id,
        target_type=data.target_type, target_id=data.target_id,
        section_ref=data.section_ref, body=data.body,
        mentions=",".join(data.mentions) if data.mentions else None,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    # Dispatch mention notifications
    for mentioned_id in data.mentions:
        try:
            from app.services.notification_service import create_notification
            await create_notification(
                db=db, workspace_id=workspace_id,
                title="You were mentioned in a comment",
                body=data.body[:100], link=f"/{data.target_type}/{data.target_id}",
                notification_type="mention",
            )
        except Exception:
            pass
    return comment


async def get_comments(target_type: str, target_id: str, db: AsyncSession) -> list[Comment]:
    result = await db.execute(
        select(Comment).where(Comment.target_type == target_type, Comment.target_id == target_id)
        .order_by(Comment.created_at)
    )
    return result.scalars().all()


async def submit_for_approval(target_type: str, target_id: str,
                               workspace_id: str, submitted_by: str, db: AsyncSession) -> ApprovalRecord:
    record = ApprovalRecord(
        workspace_id=workspace_id, target_type=target_type, target_id=target_id,
        submitted_by=submitted_by, status="pending",
    )
    db.add(record)
    await db.commit()
    return record


async def decide_approval(approval_id: str, approver_id: str, decision: str,
                          note: str, db: AsyncSession) -> ApprovalRecord:
    result = await db.execute(select(ApprovalRecord).where(ApprovalRecord.id == approval_id))
    record = result.scalar_one_or_none()
    if not record:
        raise ValueError("Approval record not found")
    record.approved_by = approver_id
    record.status = decision   # "approved" or "rejected"
    record.verdict_note = note
    record.decided_at = datetime.utcnow()
    await db.commit()
    return record
```

---

## Step 3 — API

`backend/app/api/v1/endpoints/comments.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.api.deps import get_db, get_current_user, get_current_workspace
from app.services.collaboration.comment_service import (
    CommentCreate, add_comment, get_comments, submit_for_approval, decide_approval
)

router = APIRouter(prefix="/comments", tags=["comments"])


@router.post("/", status_code=201)
async def post_comment(body: CommentCreate, db: AsyncSession = Depends(get_db),
                       current_user=Depends(get_current_user),
                       workspace=Depends(get_current_workspace)):
    comment = await add_comment(body, workspace.id, current_user.id, db)
    return {"id": comment.id, "body": comment.body, "created_at": str(comment.created_at)}


@router.get("/{target_type}/{target_id}")
async def list_comments(target_type: str, target_id: str, db: AsyncSession = Depends(get_db),
                        current_user=Depends(get_current_user)):
    comments = await get_comments(target_type, target_id, db)
    return [{"id": c.id, "body": c.body, "author": c.author_user_id, "created_at": str(c.created_at)} for c in comments]


class ApprovalRequest(BaseModel):
    target_type: str
    target_id: str

@router.post("/approvals", status_code=201)
async def submit_approval(body: ApprovalRequest, db: AsyncSession = Depends(get_db),
                          current_user=Depends(get_current_user),
                          workspace=Depends(get_current_workspace)):
    record = await submit_for_approval(body.target_type, body.target_id,
                                        workspace.id, current_user.id, db)
    return {"approval_id": record.id, "status": record.status}


class ApprovalDecision(BaseModel):
    decision: str    # "approved" | "rejected"
    note: str = ""

@router.post("/approvals/{approval_id}/decide")
async def decide(approval_id: str, body: ApprovalDecision, db: AsyncSession = Depends(get_db),
                 current_user=Depends(get_current_user)):
    record = await decide_approval(approval_id, current_user.id, body.decision, body.note, db)
    return {"approval_id": record.id, "status": record.status, "decided_at": str(record.decided_at)}
```

---

## Step 4 — Frontend CommentThread.tsx

```typescript
// frontend/src/features/collaboration/CommentThread.tsx
import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";

interface Comment { id: string; body: string; author: string; created_at: string; }

interface Props { targetType: string; targetId: string; }

export function CommentThread({ targetType, targetId }: Props) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [input, setInput] = useState("");

  useEffect(() => {
    apiClient.get(`/comments/${targetType}/${targetId}`).then(r => setComments(r.data));
  }, [targetType, targetId]);

  async function post() {
    if (!input.trim()) return;
    const mentions = [...input.matchAll(/@(\w+)/g)].map(m => m[1]);
    const res = await apiClient.post("/comments/", { target_type: targetType, target_id: targetId, body: input, mentions });
    setComments(prev => [...prev, res.data]);
    setInput("");
  }

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {comments.map(c => (
          <div key={c.id} className="bg-slate-700 rounded p-3 text-sm">
            <span className="text-slate-400 text-xs">{c.author}</span>
            <p className="text-white mt-1">{c.body}</p>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input value={input} onChange={e => setInput(e.target.value)}
          placeholder="Add comment… @mention users"
          className="flex-1 bg-slate-700 border border-slate-600 text-white rounded px-3 py-2 text-sm"
          onKeyDown={e => e.key === "Enter" && post()} />
        <button onClick={post} className="bg-blue-600 text-white px-3 py-2 rounded text-sm">Post</button>
      </div>
    </div>
  );
}
```

---

## Tests

`backend/tests/unit/collaboration/test_comment_service.py`:
```python
import pytest, asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.collaboration.comment_service import CommentCreate, add_comment

def test_add_comment_creates_record():
    db = AsyncMock()
    data = CommentCreate(target_type="blueprint", target_id="bp_001", body="Looks good!")
    added = []
    db.add = lambda x: added.append(x)
    asyncio.get_event_loop().run_until_complete(add_comment(data, "ws_001", "user_001", db))
    assert len(added) == 1
    assert added[0].body == "Looks good!"

def test_add_comment_with_mentions():
    db = AsyncMock()
    data = CommentCreate(target_type="run", target_id="run_001", body="@alice check this",
                         mentions=["alice"])
    added = []
    db.add = lambda x: added.append(x)
    asyncio.get_event_loop().run_until_complete(add_comment(data, "ws_001", "user_001", db))
    assert "alice" in (added[0].mentions or "")
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/collaboration/ -v
cd frontend && npm run build
```
