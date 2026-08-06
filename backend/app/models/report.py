"""Report model — persisted Format C resilience audits (T30/T44)."""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_jsonb = JSONB().with_variant(JSONB(), "postgresql").with_variant(SQLiteJSON(), "sqlite")


def _new_share_token() -> str:
    return secrets.token_urlsafe(24)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_run_id", "run_id"),
        Index("ix_reports_run_type", "run_id", "type"),
        Index("ix_reports_share_token", "share_token"),
    )

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: _new_report_id()
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(40), default="resilience_audit", nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[dict[str, Any]] = mapped_column(_jsonb, nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # T44: URL-safe share token — null = not shared / revoked. Set on share,
    # cleared on revoke.
    share_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def _new_report_id() -> str:
    from app.utils.ids import new_prefixed_id

    return new_prefixed_id("rpt")
