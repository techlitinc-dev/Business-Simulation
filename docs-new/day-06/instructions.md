# Day 06 — F-01: Report API Endpoint + WebSocket Progress Streaming

## Feature
F-01: Deep-Dive Report Engine

## Goal
Expose `POST /api/v1/reports/deep-dive` to enqueue the Celery report job. Publish progress to Redis and forward it over the existing WebSocket channel. `GET /api/v1/reports/{id}/status` returns job progress. `GET /api/v1/reports/{id}/download` returns the final PDF.

## Prerequisites
- Day 01–05 complete
- Existing WebSocket endpoint at `/ws/simulations/{id}` (pattern to follow)
- Existing `metering_service.py` for token + action metering
- Existing `billing_service.py` / `plans.py` for tier gating

---

## Step 1 — Create `backend/app/schemas/deep_report.py`

```python
from __future__ import annotations
from pydantic import BaseModel
from enum import Enum


class ReportJobStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DeepReportRequest(BaseModel):
    run_id: str
    report_type: str = "resilience_audit"
    # tier is derived from workspace plan — not user-supplied


class DeepReportResponse(BaseModel):
    job_id: str
    run_id: str
    status: ReportJobStatus
    tier: str
    total_sections: int
    pdf_url: str | None = None


class ReportProgressEvent(BaseModel):
    job_id: str
    section: int
    total: int
    status: str        # "writing" | "done" | "error"
    section_title: str
```

---

## Step 2 — Create `backend/app/api/v1/endpoints/deep_report.py`

```python
from __future__ import annotations
import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace, get_db
from app.schemas.deep_report import DeepReportRequest, DeepReportResponse, ReportJobStatus
from app.services.deep_report.registry import get_manifest
from app.services.deep_report.manifest import ReportTier
from app.services.metering_service import meter_action
from app.workers.report_job import generate_deep_report
from app.core.config import settings
import redis as redis_lib

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["deep-report"])

REPORT_STORAGE_DIR = settings.REPORT_STORAGE_DIR  # add to config

_PLAN_TIER_MAP = {
    "free": ReportTier.FREE,
    "pro": ReportTier.PRO,
    "business": ReportTier.ENTERPRISE,
    "enterprise": ReportTier.ENTERPRISE,
}


def _get_redis():
    return redis_lib.from_url(settings.REDIS_URL)


@router.post("/deep-dive", response_model=DeepReportResponse, status_code=202)
async def request_deep_report(
    body: DeepReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    """
    Enqueue a deep-dive report generation job.
    Tier is derived from the workspace's active plan.
    Returns job_id and initial status=queued.
    """
    plan = getattr(workspace, "plan", "free")
    tier_enum = _PLAN_TIER_MAP.get(plan, ReportTier.FREE)
    tier = tier_enum.value

    manifest = get_manifest(body.report_type)
    sections = manifest.sections_for_tier(tier_enum)

    # Meter the report generation action
    await meter_action(db, workspace.id, "deep_report_generate", cost=len(sections))

    job_id = f"dr_{uuid.uuid4().hex[:12]}"

    # Enqueue Celery task
    generate_deep_report.delay(
        job_id=job_id,
        run_id=body.run_id,
        report_type=body.report_type,
        tier=tier,
    )

    logger.info(f"[deep_report] Enqueued job={job_id} run={body.run_id} tier={tier}")

    return DeepReportResponse(
        job_id=job_id,
        run_id=body.run_id,
        status=ReportJobStatus.QUEUED,
        tier=tier,
        total_sections=len(sections),
    )


@router.get("/deep-dive/{job_id}/status", response_model=DeepReportResponse)
async def get_report_status(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """Return current progress of a deep-dive report job."""
    redis = _get_redis()
    raw = redis.get(f"deep_report:progress:{job_id}")
    if raw is None:
        raise HTTPException(status_code=404, detail="Report job not found")

    progress = json.loads(raw)
    is_done = progress.get("status") == "done" and progress.get("section") == progress.get("total")

    pdf_url = None
    if is_done:
        import os
        pdf_path = f"{REPORT_STORAGE_DIR}/{job_id}.pdf"
        if os.path.exists(pdf_path):
            pdf_url = f"/api/v1/reports/deep-dive/{job_id}/download"

    return DeepReportResponse(
        job_id=job_id,
        run_id=progress.get("run_id", ""),
        status=ReportJobStatus.COMPLETED if is_done else ReportJobStatus.IN_PROGRESS,
        tier=progress.get("tier", "free"),
        total_sections=progress.get("total", 0),
        pdf_url=pdf_url,
    )


@router.get("/deep-dive/{job_id}/download")
async def download_report(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """Return the final PDF file for a completed report job."""
    import os
    pdf_path = f"{REPORT_STORAGE_DIR}/{job_id}.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report PDF not yet available")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"report_{job_id}.pdf",
    )
```

---

## Step 3 — Register router in `app/api/v1/router.py`

Add:
```python
from app.api.v1.endpoints.deep_report import router as deep_report_router
api_router.include_router(deep_report_router)
```

---

## Step 4 — Update Celery job to save PDF on completion

In `report_job.py`, after the section loop, add:

```python
# Assemble and save PDF
import asyncio as _aio
from app.services.deep_report.assembler import assemble_report
from app.core.config import settings as _settings
import os

os.makedirs(_settings.REPORT_STORAGE_DIR, exist_ok=True)
output_path = f"{_settings.REPORT_STORAGE_DIR}/{job_id}.pdf"

async def _assemble():
    # Fetch tick_logs and mc_aggregates for the run
    async with AsyncSessionLocal() as db:
        from app.services.deep_report.data_pack import _fetch_tick_logs, _fetch_run, _extract_mc_aggregates
        run = await _fetch_run(run_id, db)
        ticks = await _fetch_tick_logs(run_id, db)
        mc = _extract_mc_aggregates(run) or {}
        return ticks, mc, getattr(run, "workspace", {})

ticks, mc, ws = asyncio.get_event_loop().run_until_complete(_assemble())
final_path = asyncio.get_event_loop().run_until_complete(
    assemble_report(results, ticks, mc, run_id, "Workspace", tier, output_path)
)
logger.info(f"[report_job] PDF saved to {final_path}")
```

---

## Step 5 — Add `REPORT_STORAGE_DIR` to config

In `backend/app/core/config.py`:
```python
REPORT_STORAGE_DIR: str = "/tmp/reports"
```

---

## Step 6 — Integration tests

`backend/tests/integration/test_deep_report_api.py`:

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_request_deep_report_queued(auth_headers, run_fixture):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/reports/deep-dive",
            json={"run_id": run_fixture.id},
            headers=auth_headers)
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["job_id"].startswith("dr_")
    assert data["total_sections"] > 0

@pytest.mark.asyncio
async def test_get_report_status_404_for_unknown_job(auth_headers):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/reports/deep-dive/unknown_job/status",
            headers=auth_headers)
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_download_404_before_completion(auth_headers):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/reports/deep-dive/nonexistent/download",
            headers=auth_headers)
    assert resp.status_code == 404
```

---

## Verification Commands

```bash
cd backend && pytest tests/integration/test_deep_report_api.py -v
cd backend && ruff check app/api/v1/endpoints/deep_report.py app/schemas/deep_report.py
```
