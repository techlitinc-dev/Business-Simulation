"""Blueprint and BlueprintVersion models — versioned Format A documents."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.ids import new_prefixed_id

_jsonb = JSONB().with_variant(JSONB(), "postgresql").with_variant(SQLiteJSON(), "sqlite")


class Blueprint(Base):
    __tablename__ = "blueprints"
    __table_args__ = (
        Index("ix_blueprints_workspace_id", "workspace_id"),
        Index("ix_blueprints_workspace_updated", "workspace_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("bp")
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    industry: Mapped[str] = mapped_column(String(120), nullable=False)
    stage: Mapped[str] = mapped_column(String(120), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    versions: Mapped[list[BlueprintVersion]] = relationship(
        back_populates="blueprint",
        cascade="all, delete-orphan",
        order_by="BlueprintVersion.version",
    )


class BlueprintVersion(Base):
    __tablename__ = "blueprint_versions"
    __table_args__ = (
        UniqueConstraint("blueprint_id", "version"),
        Index("ix_blueprint_versions_blueprint_id", "blueprint_id"),
    )

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("bpv")
    )
    blueprint_id: Mapped[str] = mapped_column(
        ForeignKey("blueprints.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(_jsonb, nullable=False)
    vulnerabilities: Mapped[list[dict[str, Any]]] = mapped_column(
        _jsonb, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    blueprint: Mapped[Blueprint] = relationship(back_populates="versions")
