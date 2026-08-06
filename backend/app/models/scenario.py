"""Scenario model — reusable marketplace blueprint templates (T42)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.ids import new_prefixed_id

_jsonb = JSONB().with_variant(JSONB(), "postgresql").with_variant(SQLiteJSON(), "sqlite")


class ScenarioCategory(StrEnum):
    MARKET_CRASH = "market_crash"
    COMPETITOR_ATTACK = "competitor_attack"
    SUPPLY_CHAIN = "supply_chain"
    REGULATORY = "regulatory"
    PANDEMIC = "pandemic"
    CUSTOM = "custom"


class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        Index("ix_scenarios_category_public", "category", "is_public"),
        Index("ix_scenarios_author", "author_workspace_id"),
    )

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("scn")
    )
    author_workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(_jsonb, nullable=False)
    clones_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
