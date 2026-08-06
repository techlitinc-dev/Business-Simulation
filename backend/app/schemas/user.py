"""User request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    """Lean profile returned by auth endpoints (register)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    is_verified: bool


class UserUpdate(BaseModel):
    """Editable profile fields (PATCH /users/me)."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    industry: str | None = Field(default=None, max_length=60)
    stage: str | None = Field(default=None, max_length=40)
    primary_fear: str | None = Field(default=None, max_length=500)


class UserRead(BaseModel):
    """Full profile including T36 onboarding state + T46 admin flag."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    is_verified: bool
    is_admin: bool
    industry: str | None
    stage: str | None
    primary_fear: str | None
    onboarding_completed: bool


class PasswordChange(BaseModel):
    """Request body for POST /users/me/password (T38)."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
