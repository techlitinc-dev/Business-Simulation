"""Unit tests for the data room service (Day 19)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

from app.services.dataroom.dataroom_service import (
    create_dataroom,
    get_dataroom,
    record_view,
    revoke_dataroom,
)

MOCK_TICKS = [{"month": 1, "revenue": 12000, "cash": 86000, "costs": 14000}]
MOCK_MC = {"survival_rate": 0.68}


class FakeRedis:
    """Minimal async redis stand-in backed by an in-memory dict."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0

    async def ttl(self, key: str) -> int:
        return 3600 if key in self._store else -2


def _patch_redis(monkeypatch: Any, fake: FakeRedis) -> None:
    import app.services.dataroom.dataroom_service as svc

    monkeypatch.setattr(svc, "get_redis", lambda: fake)
    monkeypatch.setattr(svc, "_storage_dir", lambda: "/tmp")


async def test_create_and_retrieve_dataroom(tmp_path: Path, monkeypatch: Any) -> None:
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)

    result = await create_dataroom(
        run_id="run_001",
        label="Test Room",
        expiry_days=7,
        pdf_path=None,
        tick_logs=MOCK_TICKS,
        mc_aggregates=MOCK_MC,
        workspace_name="TestCo",
        db=AsyncMock(),
    )
    assert "token" in result
    assert "download_url" in result
    assert "/download" in result["download_url"]

    meta = await get_dataroom(result["token"])
    assert meta is not None
    assert meta["run_id"] == "run_001"
    assert meta["view_count"] == 0


async def test_record_view_increments_count(tmp_path: Path, monkeypatch: Any) -> None:
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)

    result = await create_dataroom(
        run_id="run_002",
        label="Room",
        expiry_days=7,
        pdf_path=None,
        tick_logs=MOCK_TICKS,
        mc_aggregates=MOCK_MC,
        workspace_name="TestCo",
        db=AsyncMock(),
    )
    await record_view(result["token"])
    meta = await get_dataroom(result["token"])
    assert meta is not None
    assert meta["view_count"] == 1


async def test_revoke_deletes_key(tmp_path: Path, monkeypatch: Any) -> None:
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)

    result = await create_dataroom(
        run_id="run_003",
        label="Room",
        expiry_days=7,
        pdf_path=None,
        tick_logs=MOCK_TICKS,
        mc_aggregates=MOCK_MC,
        workspace_name="TestCo",
        db=AsyncMock(),
    )
    await revoke_dataroom(result["token"])
    assert await get_dataroom(result["token"]) is None


async def test_get_dataroom_unknown_token_returns_none(monkeypatch: Any) -> None:
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    assert await get_dataroom("doesnotexist") is None
