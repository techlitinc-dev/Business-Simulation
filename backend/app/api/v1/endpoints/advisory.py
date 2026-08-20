"""Advisory board endpoints: queue board review, poll results."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.agents.advisory_board import run_advisory_board
from app.api.deps import CurrentWorkspace, DbSession, get_redis
from app.services.blueprint_service import get_version_payload
from app.services.deep_report.data_pack import _extract_mc_aggregates, _fetch_run

router = APIRouter(prefix="/advisory", tags=["advisory"])

_ADVISORY_KEY = "advisory:{job_id}"


@router.post("/blueprints/{blueprint_id}/board-review", status_code=202)
async def request_board_review(
    blueprint_id: str,
    background_tasks: BackgroundTasks,
    db: DbSession,
    workspace: CurrentWorkspace,
    run_id: str | None = None,
) -> dict[str, str]:
    job_id = f"adv_{uuid.uuid4().hex[:12]}"
    background_tasks.add_task(
        _run_board_review, job_id, blueprint_id, run_id, db, workspace.id
    )
    return {"job_id": job_id, "status": "queued"}


async def _run_board_review(
    job_id: str,
    blueprint_id: str,
    run_id: str | None,
    db: DbSession,
    workspace_id: Any,
) -> None:
    redis = get_redis()
    try:
        await redis.set(
            _ADVISORY_KEY.format(job_id=job_id),
            json.dumps({"status": "running"}),
            ex=3600,
        )

        blueprint_payload = await get_version_payload(
            db,
            workspace_id=workspace_id,
            blueprint_id=blueprint_id,
            version=None,
        )
        run_summary: dict[str, Any] = {}
        if run_id:
            run = await _fetch_run(run_id, db)
            mc = _extract_mc_aggregates(run) or {}
            run_summary = {
                "survival_rate": mc.get("survival_rate", 0),
                "median_lifespan": mc.get("median_lifespan_months", 0),
            }

        result = await run_advisory_board(blueprint_payload.model_dump(mode="json"), run_summary)
        await redis.set(
            _ADVISORY_KEY.format(job_id=job_id),
            json.dumps({"status": "complete", "result": result}),
            ex=3600,
        )
    except Exception as exc:  # noqa: BLE001 - job status must always be set
        await redis.set(
            _ADVISORY_KEY.format(job_id=job_id),
            json.dumps({"status": "error", "error": str(exc)}),
            ex=3600,
        )


@router.get("/board-review/{job_id}")
async def get_board_review(
    job_id: str,
    workspace: CurrentWorkspace,
) -> dict[str, Any]:
    redis = get_redis()
    raw = await redis.get(_ADVISORY_KEY.format(job_id=job_id))
    if not raw:
        raise HTTPException(status_code=404, detail="Review job not found")
    return json.loads(raw)  # type: ignore[no-any-return]
