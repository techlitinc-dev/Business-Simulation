"""Blueprint CRUD + versioning endpoints (T17)."""

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentWorkspace, DbSession
from app.core.exceptions import StructuredOutputError
from app.schemas.blueprint import (
    BlueprintCreate,
    BlueprintDetailResponse,
    BlueprintResponse,
    BlueprintUpdate,
    BlueprintVersionCreate,
    BlueprintVersionResponse,
    ForgeReviewResponse,
)
from app.services import blueprint_service
from app.services.blueprint_service import ValidationReport

router = APIRouter(prefix="/blueprints", tags=["blueprints"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_blueprint(
    payload: BlueprintCreate,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> BlueprintDetailResponse:
    report = blueprint_service.validate_blueprint(payload.payload)
    if not report.is_valid:
        raise HTTPException(status_code=422, detail=report.model_dump())
    return await blueprint_service.create_blueprint(
        db,
        workspace_id=workspace.id,
        name=payload.name,
        industry=payload.industry,
        stage=payload.stage,
        payload=payload.payload,
    )


@router.get("")
async def list_blueprints(
    db: DbSession,
    workspace: CurrentWorkspace,
) -> list[BlueprintResponse]:
    return await blueprint_service.list_blueprints(db, workspace_id=workspace.id)


@router.get("/{blueprint_id}")
async def get_blueprint(
    blueprint_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> BlueprintDetailResponse:
    return await blueprint_service.get_blueprint_detail(
        db, workspace_id=workspace.id, blueprint_id=blueprint_id
    )


@router.patch("/{blueprint_id}")
async def update_blueprint(
    blueprint_id: str,
    payload: BlueprintUpdate,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> BlueprintResponse:
    return await blueprint_service.update_blueprint(
        db,
        workspace_id=workspace.id,
        blueprint_id=blueprint_id,
        name=payload.name,
        industry=payload.industry,
        stage=payload.stage,
    )


@router.delete("/{blueprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blueprint(
    blueprint_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> Response:
    await blueprint_service.delete_blueprint(
        db, workspace_id=workspace.id, blueprint_id=blueprint_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{blueprint_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_version(
    blueprint_id: str,
    payload: BlueprintVersionCreate,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> BlueprintVersionResponse:
    report = blueprint_service.validate_blueprint(payload.payload)
    if not report.is_valid:
        raise HTTPException(status_code=422, detail=report.model_dump())
    return await blueprint_service.add_version(
        db, workspace_id=workspace.id, blueprint_id=blueprint_id, payload=payload.payload
    )


@router.get("/{blueprint_id}/versions")
async def list_versions(
    blueprint_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> list[BlueprintVersionResponse]:
    return await blueprint_service.list_versions(
        db, workspace_id=workspace.id, blueprint_id=blueprint_id
    )


@router.get("/{blueprint_id}/validate")
async def validate_blueprint(
    blueprint_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
    version: int | None = Query(default=None, ge=1),
) -> ValidationReport:
    """Validate the current (or a pinned) version's payload. Never fails on a
    bad blueprint — it reports the issues instead."""
    payload = await blueprint_service.get_version_payload(
        db, workspace_id=workspace.id, blueprint_id=blueprint_id, version=version
    )
    return blueprint_service.validate_blueprint(payload)


@router.post("/{blueprint_id}/review")
async def review_blueprint(
    blueprint_id: str,
    db: DbSession,
    workspace: CurrentWorkspace,
) -> ForgeReviewResponse:
    """AI Forge blueprint review — persists identified vulnerabilities on the
    current version. 502 (not 500) when the LLM cannot produce valid JSON."""
    detail = await blueprint_service.get_blueprint_detail(
        db, workspace_id=workspace.id, blueprint_id=blueprint_id
    )
    try:
        from app.agents.forge import ForgeAgent
        from app.agents.llm.factory import get_llm_provider
        from app.core.config import get_settings

        agent = ForgeAgent(get_llm_provider(get_settings()))
        review, llm_response = await agent.review_blueprint(
            detail.payload.model_dump(mode="json"), reviewed_version=detail.current_version
        )
    except StructuredOutputError as exc:
        raise HTTPException(
            status_code=502, detail="Blueprint review failed: model returned invalid output"
        ) from exc

    version = await blueprint_service.persist_vulnerabilities(
        db,
        workspace_id=workspace.id,
        blueprint_id=blueprint_id,
        vulnerabilities=[
            v.model_dump(mode="json") for v in review.identified_vulnerabilities
        ],
    )
    return ForgeReviewResponse(
        overall_assessment=review.overall_assessment,
        identified_vulnerabilities=review.identified_vulnerabilities,
        reviewed_version=version,
        llm_model=llm_response.model,
        tokens_used=llm_response.prompt_tokens + llm_response.completion_tokens,
    )
