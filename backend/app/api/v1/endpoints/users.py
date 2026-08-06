"""User endpoints: profile access and updates."""

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import PasswordChange, UserRead, UserUpdate
from app.services import auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_me(payload: UserUpdate, db: DbSession, user: CurrentUser) -> UserRead:
    """Update profile fields; completing all onboarding fields flips
    ``onboarding_completed`` to True (T36)."""
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] is not None:
        user.name = data["name"].strip()

    for field in ("industry", "stage", "primary_fear"):
        if field in data:
            setattr(user, field, data[field])

    onboarding_fields = (
        user.industry is not None
        and user.stage is not None
        and user.primary_fear is not None
    )
    if onboarding_fields:
        user.onboarding_completed = True

    await db.commit()
    await db.refresh(user)
    return UserRead.model_validate(user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange, db: DbSession, user: CurrentUser
) -> Response:
    """Change the caller's password (T38)."""
    await auth_service.change_password(
        db,
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
