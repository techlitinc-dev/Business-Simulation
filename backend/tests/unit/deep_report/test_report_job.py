"""End-to-end check: the Celery report job with the mock LLM provider.

Runs the full manifest walk for FREE and PRO tiers against an empty (but
schema-created) sqlite DB. With no API key the mock provider returns ``{}``,
so every AI section must fall back to the deterministic data-only render —
the report never fails.
"""

from __future__ import annotations

from typing import Any

from app.workers.report_job import generate_deep_report


def _run(job_id: str, run_id: str, tier: str) -> dict[str, Any]:
    return generate_deep_report(job_id, run_id, "resilience_audit", tier)  # type: ignore[no-any-return]


def test_free_tier_job_completes_with_fallback() -> None:
    result = _run("job-free", "run-missing", "free")
    assert result["status"] == "complete"
    assert result["sections_completed"] == 3


def test_pro_tier_job_completes_with_fallback() -> None:
    result = _run("job-pro", "run-missing", "pro")
    assert result["status"] == "complete"
    assert result["sections_completed"] == 13


def test_enterprise_tier_job_completes_with_fallback() -> None:
    result = _run("job-ent", "run-missing", "enterprise")
    assert result["status"] == "complete"
    assert result["sections_completed"] == 21


def test_job_writes_pdf_for_missing_run() -> None:
    # PDF assembly is best-effort: with no run rows it renders an empty-data
    # report to the storage dir instead of failing the job.
    result = _run("job-pdf", "run-missing", "free")
    assert result["status"] == "complete"
    assert result["pdf_path"] is not None
    from pathlib import Path

    assert Path(result["pdf_path"]).exists()
    assert Path(result["pdf_path"]).read_bytes().startswith(b"%PDF")
    Path(result["pdf_path"]).unlink()
