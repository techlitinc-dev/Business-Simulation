from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ReportJobStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DeepReportRequest(BaseModel):
    run_id: str
    report_type: str = "resilience_audit"
    #: Report language code ("es", "fr", ...); empty/"en" = English.
    lang: str = "en"
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
    status: str  # "writing" | "done" | "error"
    section_title: str
