"""Billing models — Subscription and UsageRecord (T40/T41)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.ids import new_prefixed_id

_jsonb = JSONB().with_variant(JSONB(), "postgresql").with_variant(SQLiteJSON(), "sqlite")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("sub")
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    tier: Mapped[str] = mapped_column(String(24), default="free", nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default="active", nullable=False
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: Stripe event ids already processed (idempotency, T40).
    processed_event_ids: Mapped[list[str]] = mapped_column(
        _jsonb, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (UniqueConstraint("workspace_id", "period"),)

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("use")
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    runs_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mc_ticks_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
