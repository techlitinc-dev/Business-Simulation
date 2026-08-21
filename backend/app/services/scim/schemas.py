"""SCIM 2.0 User schemas (core user resource)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ScimUser(BaseModel):
    """SCIM 2.0 User resource — ``userName`` is the email address."""

    userName: EmailStr = Field(..., description="SCIM userName — the user's email")
    displayName: str | None = None
    active: bool = True
    externalId: str | None = None
    schemas: list[str] = [
        "urn:ietf:params:scim:schemas:core:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
    ]


class ScimUserResponse(BaseModel):
    """SCIM 2.0 User response — includes the SCIM meta block."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    userName: str
    displayName: str | None = None
    active: bool = True
    schemas: list[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    meta: dict[str, object] = {}
