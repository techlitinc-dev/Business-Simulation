"""Outbound webhook registration — workspace-scoped delivery targets."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.ids import new_prefixed_id

_jsonb = JSONB().with_variant(JSONB(), "postgresql").with_variant(SQLiteJSON(), "sqlite")


class WebhookRegistration(Base):
    __tablename__ = "webhook_registrations"
    __table_args__ = (
        Index("ix_webhook_registrations_workspace_id", "workspace_id"),
        Index("ix_webhook_registrations_workspace_active", "workspace_id", "active"),
    )

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("wh")
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_url: Mapped[str] = mapped_column(String(512), nullable=False)
    # Event types to deliver: "run.completed" | "report.ready" | "score.dropped".
    events: Mapped[list[str]] = mapped_column(_jsonb, default=list, nullable=False)
    # Signing secret for X-Forge-Signature; stored in plaintext (like api key
    # hashes are not — webhooks use a shared-secret HMAC model).
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
