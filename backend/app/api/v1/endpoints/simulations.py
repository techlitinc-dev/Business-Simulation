"""Simulation run endpoints (T25/T26/T27/T28)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentWorkspace, DbSession, get_redis
from app.core.exceptions import DomainError
from app.schemas.simulation import (
    ControlRequest,
    DecisionAppliedResponse,
    DecisionRequest,
    SimulationRunResponse,
    SimulationStartRequest,
    TickLogResponse,
)
from app.services import simulation_service
from app.services.simulation_service import (
    get_run_progress,
    get_run_ticks,
    get_workspace_run,
)

router = APIRouter(prefix="/simulations", tags=["simulations"])


def _run_response(
    run: object, progress: dict[str, object] | None = None
) -> SimulationRunResponse:
    return SimulationRunResponse.model_validate(run).model_copy(
        update={"progress": progress}
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_simulation(
    payload: SimulationStartRequest,
    db: DbSession,
    workspace: CurrentWorkspace,
    redis: Annotated[object, Depends(get_redis)],
) -> SimulationRunResponse:
    """Start a run — baseline/stress run synchronously, Monte Carlo enqueues."""
    try:
        run = await simulation_service.start_simulation(
            db, workspace_id=workspace.id, req=payload, redis=redis
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _run_response(run)


@router.get("/{run_id}")
async def get_simulation(
    run_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
    redis: Annotated[object, Depends(get_redis)],
) -> SimulationRunResponse:
    try:
        run = await get_workspace_run(db, workspace.id, run_id)
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    progress = None
    if run.mode == "monte_carlo" and run.status == "pending":
        progress = await get_run_progress(redis, run_id)
    return _run_response(run, progress)


@router.get("/{run_id}/ticks")
async def get_ticks(
    run_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> list[TickLogResponse]:
    try:
        run = await get_workspace_run(db, workspace.id, run_id)
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await get_run_ticks(db, run.id)


@router.post("/{run_id}/decide", status_code=status.HTTP_200_OK)
async def decide(
    run_id: str,
    payload: DecisionRequest,
    db: DbSession,
    workspace: CurrentWorkspace,
    redis: Annotated[object, Depends(get_redis)],
) -> DecisionAppliedResponse:
    """Apply a strategic decision to a pending hurdle and resume the run (T26)."""
    try:
        run, decision = await simulation_service.apply_decision(
            db,
            workspace_id=workspace.id,
            run_id=run_id,
            event_id=payload.event_id,
            option_id=payload.option_id,
            redis=redis,
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return DecisionAppliedResponse(
        decision_id=decision.id,
        event_id=decision.event_id,
        option_id=decision.option_id,
        run=_run_response(run),
    )


@router.post("/{run_id}/control")
async def control(
    run_id: str,
    payload: ControlRequest,
    db: DbSession,
    workspace: CurrentWorkspace,
    redis: Annotated[object, Depends(get_redis)],
) -> SimulationRunResponse:
    """Pause / resume / cancel a run (T28)."""
    try:
        run = await simulation_service.control_run(
            db, workspace_id=workspace.id, run_id=run_id, action=payload.action, redis=redis
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _run_response(run)
