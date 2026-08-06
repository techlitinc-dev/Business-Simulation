"""API key service — generation, hashing, lookup (T45)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreatedResponse, ApiKeyResponse


def generate_key() -> tuple[str, str, str]:
    """Return (full_key, prefix, key_hash) — plaintext is never persisted."""
    full_key = "fk_" + secrets.token_urlsafe(32)
    prefix = full_key[:12]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


def hash_key(full_key: str) -> str:
    return hashlib.sha256(full_key.encode()).hexdigest()


async def create_api_key(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    name: str,
    scopes: Sequence[str],
    rate_limit_rpm: int,
) -> tuple[ApiKeyCreatedResponse, str]:
    full_key, prefix, key_hash = generate_key()
    key = ApiKey(
        workspace_id=workspace_id,
        name=name.strip(),
        prefix=prefix,
        key_hash=key_hash,
        scopes=list(scopes),
        rate_limit_rpm=rate_limit_rpm,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return (
        ApiKeyCreatedResponse(
            id=key.id,
            name=key.name,
            prefix=key.prefix,
            scopes=key.scopes,
            key=full_key,
        ),
        full_key,
    )


async def list_api_keys(
    db: AsyncSession, *, workspace_id: uuid.UUID
) -> list[ApiKeyResponse]:
    rows = await db.scalars(
        select(ApiKey)
        .where(ApiKey.workspace_id == workspace_id)
        .order_by(ApiKey.created_at.desc())
    )
    return [ApiKeyResponse.model_validate(k) for k in rows]


async def revoke_api_key(
    db: AsyncSession, *, workspace_id: uuid.UUID, api_key_id: str
) -> None:
    key = await db.scalar(
        select(ApiKey).where(
            ApiKey.id == api_key_id,
            ApiKey.workspace_id == workspace_id,
        )
    )
    if key is None:
        raise DomainError(status_code=404, detail="API key not found")
    key.revoked_at = datetime.now(UTC)
    await db.commit()


async def find_active_key(db: AsyncSession, full_key: str) -> ApiKey | None:
    """Look up a key by hash; returns None if unknown or revoked."""
    key = await db.scalar(
        select(ApiKey).where(ApiKey.key_hash == hash_key(full_key))
    )
    if key is None or key.revoked_at is not None:
        return None
    key.last_used_at = datetime.now(UTC)
    await db.commit()
    return key
