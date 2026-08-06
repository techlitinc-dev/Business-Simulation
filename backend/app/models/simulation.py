"""Simulation run persistence: runs, tick logs, hurdles, decisions.

The run status enum is the single source of truth for the run lifecycle and
is shared with the API schemas and the frontend:

    pending | running | awaiting_decision | paused | completed | dead |
    cancelled | failed
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.ids import new_prefixed_id

_jsonb = JSONB().with_variant(JSONB(), "postgresql").with_variant(SQLiteJSON(), "sqlite")


class RunStatus(StrEnum):
    """Lifecycle of one simulation run (single source of truth)."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_DECISION = "awaiting_decision"
    PAUSED = "paused"
    COMPLETED = "completed"
    DEAD = "dead"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL_STATUSES = frozenset(
    {RunStatus.COMPLETED, RunStatus.DEAD, RunStatus.CANCELLED, RunStatus.FAILED}
)


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    __table_args__ = (
        Index("ix_simulation_runs_workspace_id", "workspace_id"),
        Index("ix_simulation_runs_bpv_id", "blueprint_version_id"),
        Index("ix_simulation_runs_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("run")
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    blueprint_version_id: Mapped[str] = mapped_column(
        ForeignKey("blueprint_versions.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default=RunStatus.PENDING, nullable=False
    )
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    current_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(_jsonb, default=dict, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(_jsonb, nullable=True)
    # Parked engine state between stress segments (T26); null for one-shot runs.
    state_snapshot: Mapped[dict[str, Any] | None] = mapped_column(_jsonb, nullable=True)
    # T44: visible on the public leaderboard (owner opt-in).
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TickLog(Base):
    __tablename__ = "tick_logs"
    __table_args__ = (
        UniqueConstraint("run_id", "month"),
        Index("ix_tick_logs_run_id", "run_id"),
    )

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("tick")
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    kpis: Mapped[dict[str, Any]] = mapped_column(_jsonb, nullable=False)


class SimulationEvent(Base):
    __tablename__ = "simulation_events"
    __table_args__ = (Index("ix_simulation_events_run_id", "run_id"),)

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("evt")
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    # Format B hurdle payload (spec §10) plus options_projection (T24).
    payload: Mapped[dict[str, Any]] = mapped_column(_jsonb, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (Index("ix_decisions_run_id", "run_id"),)

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("dec")
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("simulation_events.id", ondelete="CASCADE"), nullable=False
    )
    option_id: Mapped[str] = mapped_column(String(16), nullable=False)
    # The chosen option's engine projection (from options_projection).
    projection: Mapped[dict[str, Any] | None] = mapped_column(_jsonb, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
