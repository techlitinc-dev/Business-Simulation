"""Deep-Dive Report endpoints: enqueue, status polling, PDF download."""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import suppress
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import CurrentWorkspace, DbSession, get_redis
from app.core.config import get_settings
from app.schemas.deep_report import (
    DeepReportRequest,
    DeepReportResponse,
    ReportJobStatus,
)
from app.services.deep_report.manifest import ReportTier
from app.services.deep_report.registry import get_manifest
from app.workers.report_job import generate_deep_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["deep-report"])

#: Workspace plan tier -> report tier. Business maps to the full manifest.
_PLAN_TIER_MAP = {
    "free": ReportTier.FREE,
    "pro": ReportTier.PRO,
    "business": ReportTier.ENTERPRISE,
    "enterprise": ReportTier.ENTERPRISE,
}


def _report_pdf_path(job_id: str) -> Path:
    settings = get_settings()
    return Path(settings.report_storage_dir) / f"{job_id}.pdf"


@router.post("/deep-dive", response_model=DeepReportResponse, status_code=202)
async def request_deep_report(
    body: DeepReportRequest,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> DeepReportResponse:
    """
    Enqueue a deep-dive report generation job.
    Tier is derived from the workspace's active plan.
    Returns job_id and initial status=queued.
    """
    tier_enum = _PLAN_TIER_MAP.get(workspace.plan_tier, ReportTier.FREE)
    tier = tier_enum.value

    try:
        manifest = get_manifest(body.report_type)
    except KeyError as exc:
        raise HTTPException(
            status_code=422, detail=f"Unknown report type: {body.report_type}"
        ) from exc
    sections = manifest.sections_for_tier(tier_enum)

    job_id = f"dr_{uuid.uuid4().hex[:12]}"

    # Enqueue the Celery task. The worker keeps a job_id -> progress key in
    # Redis; the status endpoint polls it. Failures to reach the broker are
    # surfaced as a FAILED status rather than a 500 (dev/test parity).
    try:
        generate_deep_report.delay(
            job_id=job_id,
            run_id=body.run_id,
            report_type=body.report_type,
            tier=tier,
        )
    except Exception:  # noqa: BLE001 - Redis broker down in dev/tests
        logger.warning("deep report: enqueue failed", exc_info=True)
        # Persist a FAILED record so subsequent status polls return FAILED
        # instead of 404, and so the frontend can surface "generation failed"
        # rather than the UI hanging or spamming 404s.
        redis = get_redis()
        with suppress(Exception):
            await redis.set(
                f"deep_report:progress:{job_id}",
                json.dumps(
                    {
                        "job_id": job_id,
                        "run_id": body.run_id,
                        "tier": tier,
                        "section": 0,
                        "total": len(sections),
                        "status": "error",
                    }
                ),
                ex=3600,
            )
        return DeepReportResponse(
            job_id=job_id,
            run_id=body.run_id,
            status=ReportJobStatus.FAILED,
            tier=tier,
            total_sections=len(sections),
        )

    logger.info("deep report: enqueued job=%s run=%s tier=%s", job_id, body.run_id, tier)

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
    workspace: CurrentWorkspace,
) -> DeepReportResponse:
    """Return current progress of a deep-dive report job."""
    redis = get_redis()
    try:
        raw = await redis.get(f"deep_report:progress:{job_id}")
    except Exception:  # noqa: BLE001 - best-effort per shared contract
        raw = None
    if raw is None:
        raise HTTPException(status_code=404, detail="Report job not found")

    progress = json.loads(raw)
    stored_status = progress.get("status")

    # A stored "error" status (enqueue broker failure or worker failure) must
    # surface as FAILED, not be misreported as in-progress or 404.
    if stored_status == "error":
        is_done = False
        status = ReportJobStatus.FAILED
    else:
        is_done = (
            stored_status == "done" and progress.get("section") == progress.get("total")
        )
        status = ReportJobStatus.COMPLETED if is_done else ReportJobStatus.IN_PROGRESS

    pdf_url = None
    if is_done and _report_pdf_path(job_id).exists():
        pdf_url = f"/api/v1/reports/deep-dive/{job_id}/download"

    return DeepReportResponse(
        job_id=job_id,
        run_id=progress.get("run_id", ""),
        status=status,
        tier=progress.get("tier", "free"),
        total_sections=progress.get("total", 0),
        pdf_url=pdf_url,
    )


@router.get("/deep-dive/{job_id}/download")
async def download_report(
    job_id: str,
    workspace: CurrentWorkspace,
) -> FileResponse:
    """Return the final PDF file for a completed report job."""
    pdf_path = _report_pdf_path(job_id)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Report PDF not yet available")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"report_{job_id}.pdf",
    )
