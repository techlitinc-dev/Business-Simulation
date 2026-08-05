"""Blueprint business logic: structural validation + async DB persistence.

``validate_blueprint`` is pure Python (no DB, no I/O) so it is trivially
unit-testable; the async helpers in the second half of this module own the
versioned Blueprint/BlueprintVersion persistence for the T17 API.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.models.blueprint import Blueprint, BlueprintVersion
from app.schemas.blueprint import (
    BlueprintDetailResponse,
    BlueprintPayload,
    BlueprintResponse,
    BlueprintVersionResponse,
)

#: A healthy LTV:CAC ratio sits at or above 3:1 (spec §9 survival threshold).
LTV_CAC_THRESHOLD = 3.0
#: No single stream should hold more than this share of projected month-12 revenue.
MAX_REVENUE_CONCENTRATION = 0.7


class ValidationIssue(BaseModel):
    code: str
    severity: str
    field: str
    message: str


class ValidationReport(BaseModel):
    is_valid: bool
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []


def _issue(
    code: str, severity: str, field: str, message: str
) -> ValidationIssue:
    return ValidationIssue(code=code, severity=severity, field=field, message=message)


def validate_blueprint(payload: BlueprintPayload) -> ValidationReport:
    """Run the structural validation rules from T16 against a Format A payload."""
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    streams = payload.revenue_engine.streams
    if not streams:
        errors.append(
            _issue(
                "NO_REVENUE_STREAMS",
                "error",
                "revenue_engine.streams",
                "At least one revenue stream is required.",
            )
        )

    for stream in streams:
        base = f"revenue_engine.streams[{stream.name}]"
        if stream.cac > 0:
            ratio = stream.ltv / stream.cac
            if ratio < LTV_CAC_THRESHOLD:
                warnings.append(
                    _issue(
                        "LTV_CAC_RATIO",
                        "warning",
                        f"{base}.ltv",
                        (
                            f"Your LTV:CAC ratio is {ratio:.1f}:1. This is below the "
                            "3:1 survival threshold. Consider raising prices or reducing churn."
                        ),
                    )
                )
        if stream.ltv < stream.cac:
            errors.append(
                _issue(
                    "NEGATIVE_UNIT_ECONOMICS",
                    "error",
                    f"{base}.ltv",
                    "LTV is less than CAC, so each customer is acquired at a loss.",
                )
            )
        if (
            stream.price_point > 0
            and payload.cost_structure.variable_per_unit >= stream.price_point
        ):
            errors.append(
                _issue(
                    "NEGATIVE_CONTRIBUTION_MARGIN",
                    "error",
                    f"{base}.price_point",
                    "Variable cost per unit meets or exceeds the price point.",
                )
            )

    burn = payload.cost_structure.burn_rate_month_1
    if burn > 0:
        runway_months = payload.financials.starting_capital / burn
        if runway_months < payload.financials.target_runway_months:
            warnings.append(
                _issue(
                    "INSUFFICIENT_RUNWAY",
                    "warning",
                    "financials.starting_capital",
                    (
                        f"Starting capital covers only {runway_months:.1f} months of burn, "
                        f"below the {payload.financials.target_runway_months}-month target."
                    ),
                )
            )

    if streams:
        projected_total = sum(
            stream.price_point * stream.projected_customers_month_12
            for stream in streams
        )
        if projected_total > 0:
            largest = max(
                stream.price_point * stream.projected_customers_month_12
                for stream in streams
            )
            if largest / projected_total > MAX_REVENUE_CONCENTRATION:
                warnings.append(
                    _issue(
                        "REVENUE_CONCENTRATION",
                        "warning",
                        "revenue_engine.streams",
                        "More than 70% of projected month-12 revenue comes from a single stream.",
                    )
                )

    return ValidationReport(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


# ---------------------------------------------------------------------------
# Async persistence helpers (T17)
# ---------------------------------------------------------------------------


async def _get_workspace_blueprint(
    db: AsyncSession, workspace_id: uuid.UUID, blueprint_id: str
) -> Blueprint:
    """Load a blueprint scoped to a workspace; 404 (never 403) on any miss."""
    blueprint = await db.scalar(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.workspace_id == workspace_id,
        )
    )
    if blueprint is None:
        raise DomainError(status_code=404, detail="Blueprint not found")
    return blueprint


async def _get_workspace_version(
    db: AsyncSession, blueprint_id: str, version: int
) -> BlueprintVersion:
    version_row = await db.scalar(
        select(BlueprintVersion).where(
            BlueprintVersion.blueprint_id == blueprint_id,
            BlueprintVersion.version == version,
        )
    )
    if version_row is None:
        raise DomainError(status_code=404, detail="Blueprint version not found")
    return version_row


async def create_blueprint(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    name: str,
    industry: str,
    stage: str,
    payload: BlueprintPayload,
) -> BlueprintDetailResponse:
    blueprint = Blueprint(
        workspace_id=workspace_id,
        name=name.strip(),
        industry=industry.strip(),
        stage=stage.strip(),
        current_version=1,
    )
    db.add(blueprint)
    await db.flush()

    db.add(
        BlueprintVersion(
            blueprint_id=blueprint.id,
            version=1,
            payload=payload.model_dump(mode="json"),
        )
    )
    await db.commit()
    await db.refresh(blueprint)

    version_row = await _get_workspace_version(db, blueprint.id, 1)
    return _detail_response(blueprint, version_row)


async def list_blueprints(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> list[BlueprintResponse]:
    rows = await db.scalars(
        select(Blueprint)
        .where(Blueprint.workspace_id == workspace_id)
        .order_by(Blueprint.updated_at.desc())
    )
    return [BlueprintResponse.model_validate(bp) for bp in rows]


async def get_blueprint_detail(
    db: AsyncSession, *, workspace_id: uuid.UUID, blueprint_id: str
) -> BlueprintDetailResponse:
    blueprint = await _get_workspace_blueprint(db, workspace_id, blueprint_id)
    version_row = await _get_workspace_version(db, blueprint.id, blueprint.current_version)
    return _detail_response(blueprint, version_row)


async def update_blueprint(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    blueprint_id: str,
    name: str | None,
    industry: str | None,
    stage: str | None,
) -> BlueprintResponse:
    blueprint = await _get_workspace_blueprint(db, workspace_id, blueprint_id)
    if name is not None:
        blueprint.name = name.strip()
    if industry is not None:
        blueprint.industry = industry.strip()
    if stage is not None:
        blueprint.stage = stage.strip()
    await db.commit()
    await db.refresh(blueprint)
    return BlueprintResponse.model_validate(blueprint)


async def delete_blueprint(
    db: AsyncSession, *, workspace_id: uuid.UUID, blueprint_id: str
) -> None:
    blueprint = await _get_workspace_blueprint(db, workspace_id, blueprint_id)
    await db.delete(blueprint)
    await db.commit()


async def persist_vulnerabilities(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    blueprint_id: str,
    vulnerabilities: list[dict[str, Any]],
) -> int:
    """Store AI-Forge review results on the current version. Returns its version."""
    blueprint = await _get_workspace_blueprint(db, workspace_id, blueprint_id)
    version_row = await _get_workspace_version(db, blueprint.id, blueprint.current_version)
    version_row.vulnerabilities = vulnerabilities
    await db.commit()
    return version_row.version


async def add_version(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    blueprint_id: str,
    payload: BlueprintPayload,
) -> BlueprintVersionResponse:
    blueprint = await _get_workspace_blueprint(db, workspace_id, blueprint_id)
    next_version = blueprint.current_version + 1
    version_row = BlueprintVersion(
        blueprint_id=blueprint.id,
        version=next_version,
        payload=payload.model_dump(mode="json"),
    )
    db.add(version_row)
    blueprint.current_version = next_version
    await db.commit()
    await db.refresh(version_row)
    return BlueprintVersionResponse.model_validate(version_row)


async def list_versions(
    db: AsyncSession, *, workspace_id: uuid.UUID, blueprint_id: str
) -> list[BlueprintVersionResponse]:
    blueprint = await _get_workspace_blueprint(db, workspace_id, blueprint_id)
    rows = await db.scalars(
        select(BlueprintVersion)
        .where(BlueprintVersion.blueprint_id == blueprint.id)
        .order_by(BlueprintVersion.version.desc())
    )
    return [BlueprintVersionResponse.model_validate(row) for row in rows]


async def get_version_payload(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    blueprint_id: str,
    version: int | None,
) -> BlueprintPayload:
    blueprint = await _get_workspace_blueprint(db, workspace_id, blueprint_id)
    if version is None:
        version_row = await _get_workspace_version(db, blueprint.id, blueprint.current_version)
    else:
        version_row = await _get_workspace_version(db, blueprint.id, version)
    return BlueprintPayload.model_validate(version_row.payload)


def _detail_response(
    blueprint: Blueprint, version_row: BlueprintVersion
) -> BlueprintDetailResponse:
    return BlueprintDetailResponse(
        id=blueprint.id,
        workspace_id=str(blueprint.workspace_id),
        name=blueprint.name,
        industry=blueprint.industry,
        stage=blueprint.stage,
        current_version=blueprint.current_version,
        created_at=blueprint.created_at,
        updated_at=blueprint.updated_at,
        payload=BlueprintPayload.model_validate(version_row.payload),
        vulnerabilities=list(version_row.vulnerabilities or []),
    )
