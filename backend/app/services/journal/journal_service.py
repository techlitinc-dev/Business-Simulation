"""Decision journal business logic.

Scores each decision against the run's actual outcome:

- 1.0  — the chosen option's engine projection was positive *and* the run
         actually survived (the "beaten AI" case).
- 0.5  — the run survived even though the chosen option's projection was
         negative (management overrode a bad AI forecast).
- 0.0  — the run died.

The projection is the deterministic 12-month engine projection the strategist
attached to each option (``Decision.projection``); the outcome comes from the
run's compact result (``SimulationRun.result``).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import Decision, SimulationEvent, SimulationRun
from app.services.journal.schemas import JournalEntry, JournalSummary

logger = logging.getLogger("forge.journal")


def _is_positive_outcome(result: dict[str, Any] | None) -> bool:
    """A run "survived" when its persisted result says so."""
    if not result:
        return False
    return bool(result.get("survived", False))


def _is_positive_projection(projection: dict[str, Any] | None) -> bool:
    """The engine's projection is positive when the option survives."""
    if not projection:
        return False
    return bool(projection.get("survives", False))


def score_decision(decision: Decision, run: SimulationRun) -> float:
    """Score a single decision against the run outcome (see module docstring)."""
    positive_projection = _is_positive_projection(decision.projection)
    positive_outcome = _is_positive_outcome(run.result)

    if positive_outcome and positive_projection:
        return 1.0
    if positive_outcome:
        return 0.5
    return 0.0


async def get_run_journal(run_id: str, db: AsyncSession) -> list[JournalEntry]:
    """Return journal entries for one run, oldest decision first."""
    run = await db.scalar(select(SimulationRun).where(SimulationRun.id == run_id))
    if run is None:
        return []

    decisions = (
        await db.scalars(
            select(Decision).where(Decision.run_id == run_id).order_by(Decision.applied_at)
        )
    ).all()

    events = (
        await db.scalars(
            select(SimulationEvent).where(SimulationEvent.run_id == run_id)
        )
    ).all()
    event_month = {e.id: e.month for e in events}

    outcome = dict(run.result) if run.result else {}
    entries: list[JournalEntry] = []
    for d in decisions:
        score = score_decision(d, run)
        projection = dict(d.projection) if d.projection else {}
        entries.append(
            JournalEntry(
                decision_id=d.id,
                run_id=run_id,
                month=event_month.get(d.event_id),
                option_chosen=d.option_id,
                option_name=projection.get("name"),
                beat_ai=score == 1.0,
                actual_outcome=outcome,
                score=score,
            )
        )
    return entries


async def get_workspace_journal_summary(
    workspace_id: str, db: AsyncSession
) -> JournalSummary:
    """Aggregate decision quality across all runs in a workspace."""
    run_ids = (
        await db.scalars(
            select(SimulationRun.id).where(SimulationRun.workspace_id == workspace_id)
        )
    ).all()

    total = 0
    beat_ai = 0
    for run_id in run_ids:
        entries = await get_run_journal(str(run_id), db)
        total += len(entries)
        beat_ai += sum(1 for e in entries if e.beat_ai)

    pct = round((beat_ai / total * 100) if total > 0 else 0, 1)
    return JournalSummary(
        total_decisions=total,
        beat_ai_count=beat_ai,
        beat_ai_pct=pct,
        summary=f"You beat the AI's recommended path in {beat_ai} of {total} decisions",
    )
