# Day 25 — F-10: Portfolio DB Model + Workspace Hierarchy

## Feature
F-10: Portfolio & Cohort Mode

## Goal
Create the Portfolio model (parent org containing N company workspaces) and service layer that aggregates resilience scores, survival rates, and drift alerts across all member workspaces.

---

## Step 1 — DB Models

`backend/app/models/portfolio.py`:
```python
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(String, primary_key=True, default=lambda: f"pf_{uuid.uuid4().hex[:12]}")
    name = Column(String, nullable=False)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    memberships = relationship("PortfolioMembership", back_populates="portfolio", lazy="selectin")


class PortfolioMembership(Base):
    __tablename__ = "portfolio_memberships"
    id = Column(String, primary_key=True, default=lambda: f"pm_{uuid.uuid4().hex[:12]}")
    portfolio_id = Column(String, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=True)      # company name override
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    portfolio = relationship("Portfolio", back_populates="memberships")
```

---

## Step 2 — Migration

`backend/alembic/versions/i0j1k2l3m4n5_portfolio_tables.py`:
```python
"""add portfolio tables
Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
"""
from alembic import op
import sqlalchemy as sa

revision = 'i0j1k2l3m4n5'
down_revision = 'h9i0j1k2l3m4'

def upgrade():
    op.create_table('portfolios',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('owner_user_id', sa.String(), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id']),
    )
    op.create_table('portfolio_memberships',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('portfolio_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_pm_portfolio_id', 'portfolio_memberships', ['portfolio_id'])
    op.create_index('ix_pm_workspace_id', 'portfolio_memberships', ['workspace_id'])

def downgrade():
    op.drop_table('portfolio_memberships')
    op.drop_table('portfolios')
```

---

## Step 3 — Portfolio Service

`backend/app/services/portfolio/__init__.py` — empty

`backend/app/services/portfolio/schemas.py`:
```python
from pydantic import BaseModel
from typing import Optional


class PortfolioCreate(BaseModel):
    name: str


class WorkspaceSummary(BaseModel):
    workspace_id: str
    label: str
    resilience_score: Optional[float] = None
    survival_rate: Optional[float] = None
    drift_alert: bool = False
    last_run_at: Optional[str] = None


class PortfolioSummary(BaseModel):
    portfolio_id: str
    name: str
    member_count: int
    workspaces: list[WorkspaceSummary]
    avg_resilience_score: Optional[float] = None
```

`backend/app/services/portfolio/portfolio_service.py`:
```python
from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.portfolio import Portfolio, PortfolioMembership
from app.models.simulation import SimulationRun
from app.services.portfolio.schemas import PortfolioCreate, PortfolioSummary, WorkspaceSummary
import uuid


async def create_portfolio(name: str, owner_user_id: str, db: AsyncSession) -> Portfolio:
    portfolio = Portfolio(name=name, owner_user_id=owner_user_id)
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


async def add_workspace(portfolio_id: str, workspace_id: str, label: str, db: AsyncSession) -> PortfolioMembership:
    membership = PortfolioMembership(
        portfolio_id=portfolio_id, workspace_id=workspace_id, label=label or workspace_id
    )
    db.add(membership)
    await db.commit()
    return membership


async def remove_workspace(portfolio_id: str, workspace_id: str, db: AsyncSession):
    result = await db.execute(
        select(PortfolioMembership).where(
            PortfolioMembership.portfolio_id == portfolio_id,
            PortfolioMembership.workspace_id == workspace_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership:
        await db.delete(membership)
        await db.commit()


async def get_portfolio_summary(portfolio_id: str, db: AsyncSession) -> PortfolioSummary | None:
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return None

    workspace_summaries: list[WorkspaceSummary] = []
    for membership in portfolio.memberships:
        ws_id = membership.workspace_id
        # Get latest completed run for this workspace
        run_result = await db.execute(
            select(SimulationRun)
            .where(SimulationRun.workspace_id == ws_id)
            .order_by(SimulationRun.created_at.desc())
            .limit(1)
        )
        latest_run = run_result.scalar_one_or_none()

        score = None
        survival = None
        last_run_at = None
        drift_alert = False

        if latest_run:
            mc = latest_run.mc_result or {}
            survival = mc.get("survival_rate")
            last_run_at = latest_run.created_at.isoformat() if latest_run.created_at else None
            if survival is not None:
                from app.engine.metrics import resilience_score
                score = resilience_score({"survival_rate": survival, "median_lifespan": mc.get("median_lifespan", 0)})

        workspace_summaries.append(WorkspaceSummary(
            workspace_id=ws_id, label=membership.label or ws_id,
            resilience_score=round(score, 1) if score else None,
            survival_rate=survival, drift_alert=drift_alert, last_run_at=last_run_at,
        ))

    scores = [ws.resilience_score for ws in workspace_summaries if ws.resilience_score is not None]
    avg = round(sum(scores) / len(scores), 1) if scores else None

    return PortfolioSummary(
        portfolio_id=portfolio_id, name=portfolio.name,
        member_count=len(workspace_summaries),
        workspaces=sorted(workspace_summaries, key=lambda w: w.resilience_score or 0, reverse=True),
        avg_resilience_score=avg,
    )
```

---

## Step 4 — Tests

`backend/tests/unit/portfolio/test_portfolio_service.py`:
```python
import pytest, asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.portfolio.portfolio_service import get_portfolio_summary


def test_get_portfolio_summary_returns_none_for_unknown():
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)
    result = asyncio.get_event_loop().run_until_complete(get_portfolio_summary("pf_unknown", db))
    assert result is None


def test_get_portfolio_summary_sorts_by_score():
    # Create a portfolio with 2 workspaces, different scores
    portfolio = MagicMock()
    portfolio.id = "pf_001"
    portfolio.name = "Test Portfolio"
    portfolio.memberships = [
        MagicMock(workspace_id="ws_001", label="Company A"),
        MagicMock(workspace_id="ws_002", label="Company B"),
    ]

    # Run results: ws_001 has higher score
    run_a = MagicMock(); run_a.mc_result = {"survival_rate": 0.80, "median_lifespan": 22}; run_a.created_at = None
    run_b = MagicMock(); run_b.mc_result = {"survival_rate": 0.45, "median_lifespan": 14}; run_b.created_at = None

    db = AsyncMock()
    calls = [0]
    async def execute_mock(q):
        mock = MagicMock()
        if calls[0] == 0:
            mock.scalar_one_or_none.return_value = portfolio
        elif calls[0] % 2 == 1:
            mock.scalar_one_or_none.return_value = run_a
        else:
            mock.scalar_one_or_none.return_value = run_b
        calls[0] += 1
        return mock
    db.execute = execute_mock

    result = asyncio.get_event_loop().run_until_complete(get_portfolio_summary("pf_001", db))
    assert result is not None
    assert result.workspaces[0].workspace_id == "ws_001"  # highest score first
```

---

## Verification Commands
```bash
cd backend && alembic upgrade head
cd backend && pytest tests/unit/portfolio/ -v
cd backend && ruff check app/services/portfolio/ app/models/portfolio.py
```
