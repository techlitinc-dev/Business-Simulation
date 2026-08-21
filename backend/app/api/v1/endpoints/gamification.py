"""Gamification endpoints — achievements + certification download."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import func, select

from app.api.deps import CurrentUser, CurrentWorkspace, DbSession
from app.core.exceptions import DomainError
from app.models.simulation import SimulationRun
from app.services.gamification.achievements import Achievement, check_achievements
from app.services.gamification.certification import generate_certification
from app.services.journal.journal_service import get_workspace_journal_summary
from app.services.simulation_service import get_workspace_run

router = APIRouter(prefix="/gamification", tags=["gamification"])


def _achievement_out(a: Achievement) -> dict[str, str]:
    return {
        "id": a.id,
        "title": a.title,
        "description": a.description,
        "icon": a.icon,
    }


@router.get("/achievements")
async def get_achievements(
    db: DbSession, user: CurrentUser, workspace: CurrentWorkspace
) -> list[dict[str, str]]:
    """Achievements earned by this workspace, from real run stats."""
    total_runs = int(
        await db.scalar(
            select(func.count(SimulationRun.id)).where(
                SimulationRun.workspace_id == workspace.id
            )
        )
        or 0
    )
    summary = await get_workspace_journal_summary(str(workspace.id), db)

    # Cohort percentile: not computed yet — default to a neutral 50 so the
    # top_decile badge is only awarded once leaderboard percentiles exist.
    context = {
        "total_runs": total_runs,
        "beat_ai_count": summary.beat_ai_count,
        "demand_shocks_survived": 0,
        "cohort_percentile": 50,
    }
    return [_achievement_out(a) for a in check_achievements(context)]


@router.post("/certification/{run_id}")
async def get_certification(
    run_id: str, db: DbSession, user: CurrentUser, workspace: CurrentWorkspace
) -> Response:
    """Generate a certification PDF for a completed run in this workspace."""
    try:
        run = await get_workspace_run(db, workspace.id, run_id)
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    result = run.result or {}
    score = float(result.get("resilience_score", 72.0))
    percentile = 64.0  # replaced by real cohort percentile when available
    pdf = generate_certification(workspace.name, score, percentile, run_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=certification_{run_id}.pdf"
        },
    )
