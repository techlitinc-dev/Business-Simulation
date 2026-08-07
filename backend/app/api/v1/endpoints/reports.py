"""Report endpoints (T30/T32/T33/T44)."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentWorkspace, DbSession
from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models.report import Report
from app.models.simulation import SimulationRun
from app.schemas.report import (
    ComparisonResponse,
    ReportResponse,
    SharedReportResponse,
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/simulations/{run_id}/report")
async def get_report(
    run_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> ReportResponse:
    """Return the resilience audit, generating + persisting on first call."""
    try:
        report = await report_service.generate_resilience_audit(
            db, workspace_id=workspace.id, run_id=run_id
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return report_service.report_response(report)


@router.post("/simulations/{run_id}/report/export", status_code=201)
async def export_report(
    run_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> dict[str, str]:
    """Render the report to PDF, save it, and return a pdf_url."""
    try:
        report = await report_service.generate_resilience_audit(
            db, workspace_id=workspace.id, run_id=run_id
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    from app.utils.pdf import render_report_pdf

    settings = get_settings()
    storage_dir = Path(settings.report_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = f"report_{run_id}.pdf"
    file_path = storage_dir / filename

    try:
        pdf_bytes = render_report_pdf(report.content_md, title="The Forge — Resilience Audit")
        file_path.write_bytes(pdf_bytes)
    except Exception as exc:  # noqa: BLE001 - weasyprint may fail in bare envs
        raise HTTPException(status_code=500, detail="PDF rendering failed") from exc

    report.pdf_path = str(file_path)
    await db.commit()
    # Serve from the backend's static /reports mount (frontend_url is the SPA
    # origin; the SPA nginx doesn't host PDFs).
    return {"pdf_url": f"/reports/{filename}"}


@router.post("/simulations/{run_id}/report/share", status_code=201)
async def share_report(
    run_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> dict[str, object]:
    """Create a persistent share token for the report (T44)."""
    try:
        report = await report_service.generate_resilience_audit(
            db, workspace_id=workspace.id, run_id=run_id
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    from app.models.report import _new_share_token

    if not report.share_token:
        report.share_token = _new_share_token()
        await db.commit()
        await db.refresh(report)

    settings = get_settings()
    share_url = f"{settings.frontend_url}/shared/reports/{report.share_token}"
    return {"share_url": share_url, "token": report.share_token}


@router.delete("/simulations/{run_id}/report/share", status_code=204)
async def revoke_report_share(
    run_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> None:
    """Revoke the report's share token (subsequent public GET → 404)."""
    try:
        report = await report_service.generate_resilience_audit(
            db, workspace_id=workspace.id, run_id=run_id
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    report.share_token = None
    await db.commit()
    return None


@router.get("/shared/{token}", response_model=SharedReportResponse)
async def shared_report(token: str, db: DbSession) -> SharedReportResponse:
    """Public endpoint — no auth. Looks up the report by its share token."""
    from app.models.blueprint import Blueprint, BlueprintVersion

    report = await db.scalar(
        select(Report).where(Report.share_token == token)
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    run = await db.get(SimulationRun, report.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Report not found")

    version = await db.get(BlueprintVersion, run.blueprint_version_id)
    blueprint_name = ""
    if version is not None:
        blueprint = await db.get(Blueprint, version.blueprint_id)
        blueprint_name = blueprint.name if blueprint is not None else ""

    return SharedReportResponse(
        blueprint_name=blueprint_name,
        completed_at=run.finished_at or run.created_at,
        content_md=report.content_md,
        content_json=report.content_json,
    )


@router.get("/compare")
async def compare_reports(
    a: str,
    b: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> ComparisonResponse:
    """Compare two completed Monte Carlo/stress runs (V1 vs V2)."""
    try:
        result = await report_service.compare_runs(
            db, workspace_id=workspace.id, run_a_id=a, run_b_id=b
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return result
