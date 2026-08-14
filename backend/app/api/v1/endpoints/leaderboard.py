"""Public leaderboard endpoint (T44)."""

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.report import Report
from app.models.simulation import SimulationRun
from app.models.workspace import Workspace
from app.schemas.report import LeaderboardEntry, LeaderboardResponse

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def leaderboard(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> LeaderboardResponse:
    """Top public Monte Carlo runs by resilience score (no auth)."""
    rows = await db.execute(
        select(SimulationRun, Workspace, Blueprint, Report.share_token)
        .join(Workspace, Workspace.id == SimulationRun.workspace_id)
        .join(BlueprintVersion, BlueprintVersion.id == SimulationRun.blueprint_version_id)
        .join(Blueprint, Blueprint.id == BlueprintVersion.blueprint_id)
        .outerjoin(Report, Report.run_id == SimulationRun.id)
        .where(
            SimulationRun.mode == "monte_carlo",
            SimulationRun.status == "completed",
            SimulationRun.is_public.is_(True),
        )
        .order_by(
            SimulationRun.result["resilience_score"].as_integer().desc(),
            SimulationRun.result["survival_rate"].as_float().desc(),
        )
        .limit(limit)
    )
    entries = [
        LeaderboardEntry(
            rank=i + 1,
            run_id=run.id,
            workspace_name=ws.name,
            blueprint_name=bp.name,
            resilience_score=int((run.result or {}).get("resilience_score", 0)),
            survival_rate=float((run.result or {}).get("survival_rate", 0.0)),
            median_lifespan_months=int(
                (run.result or {}).get("median_lifespan_months", 0)
            ),
            completed_at=run.finished_at or run.created_at,
            share_token=share_token,
        )
        for i, (run, ws, bp, share_token) in enumerate(rows.all())
    ]
    return LeaderboardResponse(entries=entries)
