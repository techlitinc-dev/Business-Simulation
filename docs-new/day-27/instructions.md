# Day 27 — F-10: SSO Scaffold (SAML/OIDC) + SCIM-Lite

## Feature
F-10: Portfolio & Cohort Mode

## Goal
Implement SAML/OIDC callback stubs that create/link user accounts via the existing auth service, and a SCIM `/Users` endpoint for automated seat provisioning.

---

## Step 1 — SSO endpoint stub

`backend/app/api/v1/endpoints/sso.py`:
```python
"""
SSO (SAML/OIDC) callback stubs.
Production wiring requires IdP configuration — these endpoints handle the
callback and create/link user accounts using the existing auth service.
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.api.deps import get_db
from app.services.auth_service import get_user_by_email, create_user
from app.core.security import create_access_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sso", tags=["sso"])


@router.get("/oidc/callback")
async def oidc_callback(
    code: str,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    OIDC authorization code callback.
    In production: exchange code for tokens with IdP, extract user claims.
    Stub: returns example response for testing.
    """
    # Production: exchange code via httpx to IdP token endpoint
    # Extract email/sub from id_token claims
    # For now — return stub response
    logger.info(f"[sso] OIDC callback received code={code[:8]}...")
    return {
        "message": "OIDC callback received. Configure OIDC_CLIENT_ID and OIDC_CLIENT_SECRET in env.",
        "next": "POST /api/v1/sso/oidc/exchange with your IdP token"
    }


@router.post("/oidc/exchange")
async def oidc_exchange(
    email: str,
    external_id: str,
    display_name: str = "",
    db: AsyncSession = Depends(get_db),
):
    """
    Create or link a user account from OIDC claims.
    Returns a JWT access token.
    """
    user = await get_user_by_email(email, db)
    if not user:
        user = await create_user(email=email, display_name=display_name,
                                  password=None, db=db, is_sso=True)
        logger.info(f"[sso] Created new user via SSO: {email}")
    else:
        logger.info(f"[sso] Linked existing user via SSO: {email}")

    token = create_access_token({"sub": user.id, "email": user.email})
    return {"access_token": token, "token_type": "bearer", "user_id": user.id}
```

---

## Step 2 — SCIM Service

`backend/app/services/scim/__init__.py` — empty

`backend/app/services/scim/schemas.py`:
```python
from pydantic import BaseModel, EmailStr
from typing import Optional


class ScimUser(BaseModel):
    userName: str               # email address
    displayName: Optional[str] = None
    active: bool = True
    externalId: Optional[str] = None


class ScimUserResponse(BaseModel):
    id: str
    userName: str
    displayName: Optional[str]
    active: bool
    schemas: list[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    meta: dict = {}
```

`backend/app/services/scim/scim_service.py`:
```python
from __future__ import annotations
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth_service import get_user_by_email, create_user, deactivate_user
from app.services.scim.schemas import ScimUser, ScimUserResponse

logger = logging.getLogger(__name__)


async def provision_user(scim_user: ScimUser, workspace_id: str, db: AsyncSession) -> ScimUserResponse:
    """Create a new user account via SCIM and add to workspace."""
    from app.services.workspace_service import add_member
    user = await get_user_by_email(scim_user.userName, db)
    if not user:
        user = await create_user(
            email=scim_user.userName,
            display_name=scim_user.displayName or scim_user.userName,
            password=None, db=db, is_sso=True
        )
        logger.info(f"[scim] Provisioned user: {scim_user.userName}")
    await add_member(workspace_id=workspace_id, user_id=user.id, role="member", db=db)
    return ScimUserResponse(id=user.id, userName=user.email,
                            displayName=user.display_name, active=True)


async def deprovision_user(user_id: str, db: AsyncSession) -> bool:
    """Deactivate (not delete) a user account."""
    result = await deactivate_user(user_id, db)
    logger.info(f"[scim] Deprovisioned user: {user_id}")
    return result
```

---

## Step 3 — SCIM API endpoints

`backend/app/api/v1/endpoints/scim.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.services.scim.schemas import ScimUser, ScimUserResponse
from app.services.scim.scim_service import provision_user, deprovision_user
from app.core.config import settings

router = APIRouter(prefix="/scim/v2", tags=["scim"])


def _verify_scim_token(authorization: str = Header(...)):
    """Verify SCIM bearer token."""
    expected = f"Bearer {settings.SCIM_TOKEN}"
    if authorization != expected:
        raise HTTPException(401, "Invalid SCIM token")


@router.post("/Users", status_code=201, response_model=ScimUserResponse)
async def create_scim_user(
    body: ScimUser,
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(_verify_scim_token),
):
    return await provision_user(body, workspace_id, db)


@router.patch("/Users/{user_id}")
async def patch_scim_user(
    user_id: str,
    active: bool = True,
    db: AsyncSession = Depends(get_db),
    _=Depends(_verify_scim_token),
):
    if not active:
        await deprovision_user(user_id, db)
    return {"id": user_id, "active": active}


@router.delete("/Users/{user_id}", status_code=204)
async def delete_scim_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(_verify_scim_token),
):
    await deprovision_user(user_id, db)
```

---

## Step 4 — Add to config

```python
# app/core/config.py
SCIM_TOKEN: str = "changeme-scim-secret"
OIDC_CLIENT_ID: str = ""
OIDC_CLIENT_SECRET: str = ""
```

---

## Step 5 — Tests

`backend/tests/integration/test_scim_api.py`:
```python
import pytest
from httpx import AsyncClient
from app.main import app

SCIM_HEADERS = {"Authorization": "Bearer changeme-scim-secret"}

@pytest.mark.asyncio
async def test_scim_provision_user(workspace_fixture):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/scim/v2/Users?workspace_id={workspace_fixture.id}",
            json={"userName": "newuser@example.com", "displayName": "New User", "active": True},
            headers=SCIM_HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["userName"] == "newuser@example.com"
    assert data["active"] is True

@pytest.mark.asyncio
async def test_scim_invalid_token():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/scim/v2/Users?workspace_id=ws_001",
            json={"userName": "test@example.com", "active": True},
            headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_scim_deprovision_user(user_fixture):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.delete(f"/api/v1/scim/v2/Users/{user_fixture.id}",
                                   headers=SCIM_HEADERS)
    assert resp.status_code == 204
```

---

## Verification Commands
```bash
cd backend && pytest tests/integration/test_scim_api.py -v
cd backend && ruff check app/api/v1/endpoints/sso.py app/api/v1/endpoints/scim.py app/services/scim/
```
