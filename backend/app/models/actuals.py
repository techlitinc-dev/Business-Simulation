"""ActualsRecord model — user-uploaded actuals vs. simulated projections."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.ids import new_prefixed_id

_jsonb = JSONB().with_variant(JSONB(), "postgresql").with_variant(SQLiteJSON(), "sqlite")


class ActualsRecord(Base):
    __tablename__ = "actuals_records"
    __table_args__ = (
        Index("ix_actuals_blueprint_id", "blueprint_id"),
        Index("ix_actuals_workspace_id", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("act")
    )
    blueprint_id: Mapped[str] = mapped_column(
        ForeignKey("blueprints.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-based month index
    period_label: Mapped[str | None] = mapped_column(String(40), nullable=True)  # e.g. "2024-01"
    fields: Mapped[dict[str, Any]] = mapped_column(_jsonb, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
