"""Report endpoints (T30/T32/T33)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.api.deps import CurrentWorkspace, DbSession
from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models.report import Report
from app.schemas.report import (
    ComparisonResponse,
    ReportResponse,
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])

_SHARE_SALT = "report-share"
_SHARE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def _share_serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.jwt_secret_key, salt=_SHARE_SALT)


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
    return {"pdf_url": f"{settings.frontend_url}/reports/{filename}"}


@router.post("/simulations/{run_id}/report/share", status_code=201)
async def share_report(
    run_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> dict[str, object]:
    """Create a signed shareable link (7-day expiry)."""
    try:
        report = await report_service.generate_resilience_audit(
            db, workspace_id=workspace.id, run_id=run_id
        )
    except DomainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    token = _share_serializer().dumps(
        {"run_id": run_id, "report_id": report.id}
    )
    expires_at = datetime.now(UTC) + timedelta(seconds=_SHARE_MAX_AGE_SECONDS)
    settings = get_settings()
    share_url = f"{settings.frontend_url}/reports/shared/{token}"
    return {
        "share_url": share_url,
        "token": token,
        "expires_at": expires_at.isoformat(),
    }


@router.get("/shared/{token}")
async def shared_report(token: str, db: DbSession) -> ReportResponse:
    """Public endpoint — no auth. Verifies the signed share token."""
    try:
        payload = _share_serializer().loads(
            token, max_age=_SHARE_MAX_AGE_SECONDS
        )
    except SignatureExpired:
        raise HTTPException(status_code=410, detail="Share link expired") from None
    except BadSignature:
        raise HTTPException(status_code=404, detail="Invalid share link") from None

    report = await db.get(Report, payload.get("report_id", ""))
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report_service.report_response(report)


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
