"""SCIM 2.0 provisioning endpoints (protected by a shared bearer token)."""

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.deps import DbSession
from app.core.config import get_settings
from app.services.scim.schemas import ScimUser, ScimUserResponse
from app.services.scim.scim_service import (
    deprovision_user,
    get_scim_user,
    provision_user,
)

router = APIRouter(prefix="/scim/v2", tags=["scim"])


def _verify_scim_token(
    authorization: str | None = Header(default=None),
) -> None:
    """Require the configured SCIM bearer token (constant-time comparison)."""
    settings = get_settings()
    expected = f"Bearer {settings.scim_token}"
    if authorization is None or authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid SCIM token")


@router.post(
    "/Users", status_code=201, response_model=ScimUserResponse
)
async def create_scim_user(
    body: ScimUser,
    workspace_id: str,
    db: DbSession,
    _: None = Depends(_verify_scim_token),
) -> ScimUserResponse:
    return await provision_user(body, workspace_id, db)


@router.patch("/Users/{user_id}", response_model=ScimUserResponse)
async def patch_scim_user(
    user_id: str,
    body: dict[str, object],
    db: DbSession,
    _: None = Depends(_verify_scim_token),
) -> ScimUserResponse:
    """SCIM PATCH — ``active`` flag only (deactivate/activate)."""
    active = body.get("active", True)
    if not active:
        await deprovision_user(user_id, db)
    return await get_scim_user(user_id, db)


@router.delete("/Users/{user_id}", status_code=204)
async def delete_scim_user(
    user_id: str,
    db: DbSession,
    _: None = Depends(_verify_scim_token),
) -> None:
    await deprovision_user(user_id, db)
