"""SSO (OIDC) callback endpoints.

Production wiring requires IdP configuration — these endpoints handle the
callback and create/link user accounts using the existing auth service.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.security import create_access_token
from app.services.auth_service import create_sso_user, get_user_by_email

logger = logging.getLogger("forge.sso")

router = APIRouter(prefix="/sso", tags=["sso"])


class OidcExchangeRequest(BaseModel):
    """Identity claims from the IdP (exchanged code is handled upstream)."""

    email: str
    external_id: str
    display_name: str = ""


@router.get("/oidc/callback")
async def oidc_callback(code: str, state: str | None = None) -> dict[str, str]:
    """OIDC authorization code callback.

    In production: exchange ``code`` for tokens with the IdP token endpoint
    (httpx) and extract email/sub from the id_token claims, then call
    ``/oidc/exchange``. Stub: confirms the callback was received.
    """
    logger.info("[sso] OIDC callback received code=%s...", code[:8])
    return {
        "message": (
            "OIDC callback received. Configure OIDC_CLIENT_ID and "
            "OIDC_CLIENT_SECRET in env."
        ),
        "next": "POST /api/v1/sso/oidc/exchange with your IdP token",
    }


@router.post("/oidc/exchange")
async def oidc_exchange(
    payload: OidcExchangeRequest, db: DbSession
) -> dict[str, object]:
    """Create or link a user account from OIDC claims. Returns a JWT."""
    user = await get_user_by_email(db, payload.email)
    if user is None:
        user = await create_sso_user(
            db, email=payload.email, name=payload.display_name or None
        )
        await db.commit()
        logger.info("[sso] Created new user via SSO: %s", payload.email)
    elif not user.is_active:
        raise HTTPException(
            status_code=401, detail="Account is deactivated"
        )
    else:
        logger.info("[sso] Linked existing user via SSO: %s", payload.email)

    token = create_access_token(str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
    }
