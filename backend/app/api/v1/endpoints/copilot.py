"""Copilot endpoint: grounded Q&A over a simulation run."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import CurrentWorkspace, DbSession
from app.services.copilot.copilot_service import chat

router = APIRouter(prefix="/simulations", tags=["copilot"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/{run_id}/chat")
async def copilot_chat(
    run_id: str,
    body: ChatRequest,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> dict[str, Any]:
    return await chat(run_id, body.question, db, body.history)
