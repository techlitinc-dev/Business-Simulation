"""BenchmarkSnapshot model — anonymized run outcomes for cohort comparison."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.ids import new_prefixed_id

_jsonb = JSONB().with_variant(JSONB(), "postgresql").with_variant(SQLiteJSON(), "sqlite")


class BenchmarkSnapshot(Base):
    __tablename__ = "benchmark_snapshots"
    __table_args__ = (
        Index("ix_benchmark_industry", "industry"),
        Index("ix_benchmark_stage", "stage"),
    )

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: new_prefixed_id("bm")
    )
    # Anonymized — no workspace/user id stored.
    industry: Mapped[str | None] = mapped_column(String(60), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    survival_rate: Mapped[float] = mapped_column(Float, nullable=False)
    median_lifespan: Mapped[float] = mapped_column(Float, nullable=False)
    resilience_score: Mapped[float] = mapped_column(Float, nullable=False)
    kill_vectors: Mapped[list[dict[str, Any]]] = mapped_column(
        _jsonb, default=list, nullable=True
    )  # top kill vectors (no business data)
    run_months: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    opted_in: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
