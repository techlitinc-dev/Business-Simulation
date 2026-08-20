"""Portfolio models — group workspaces for investor oversight."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.ids import new_prefixed_id

_jsonb = JSONB().with_variant(JSONB(), "postgresql").with_variant(SQLiteJSON(), "sqlite")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("pf")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    settings: Mapped[dict[str, Any]] = mapped_column(_jsonb, default=dict, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memberships: Mapped[list[PortfolioMembership]] = relationship(
        back_populates="portfolio", lazy="selectin", cascade="all, delete-orphan"
    )


class PortfolioMembership(Base):
    __tablename__ = "portfolio_memberships"
    __table_args__ = (
        Index("ix_pm_portfolio_id", "portfolio_id"),
        Index("ix_pm_workspace_id", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("pm")
    )
    portfolio_id: Mapped[str] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)  # company name override
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolio: Mapped[Portfolio] = relationship(back_populates="memberships")
