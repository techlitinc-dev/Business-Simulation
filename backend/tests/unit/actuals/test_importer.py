"""Unit tests for the actuals CSV importer (Day 12)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.db.base import Base
from app.models.actuals import ActualsRecord
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.workspace import Workspace
from app.services.actuals.importer import _parse_csv, _validate_row, import_actuals
from app.services.actuals.schemas import ActualsUploadRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SAMPLE_CSV = """month,revenue,costs,cash,churn_rate
1,12000,14000,86000,0.05
2,15000,14200,86800,0.04
3,invalid,14500,89000,0.04
"""


def test_parse_csv_basic() -> None:
    rows = _parse_csv(SAMPLE_CSV, {})
    assert len(rows) == 3
    assert rows[0]["month"] == "1"
    assert rows[0]["revenue"] == "12000"


def test_parse_csv_with_column_mapping() -> None:
    csv = "Month,Monthly Revenue\n1,12000\n2,15000"
    rows = _parse_csv(csv, {"Month": "month", "Monthly Revenue": "revenue"})
    assert rows[0]["month"] == "1"
    assert rows[0]["revenue"] == "12000"


def test_validate_row_valid() -> None:
    row = {"month": "1", "revenue": "12000", "costs": "14000"}
    result = _validate_row(row, 2)
    assert result.errors == []


def test_validate_row_missing_month() -> None:
    row = {"revenue": "12000"}
    result = _validate_row(row, 2)
    assert any("month" in e for e in result.errors)


def test_validate_row_invalid_number() -> None:
    row = {"month": "1", "revenue": "not_a_number"}
    result = _validate_row(row, 2)
    assert any("revenue" in e for e in result.errors)


async def test_import_actuals_created_count() -> None:
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()  # sync method on the session
    mock_db.commit = AsyncMock()

    req = ActualsUploadRequest(
        blueprint_id="bp_001",
        csv_content="month,revenue\n1,12000\n2,15000",
        column_mapping={},
    )
    result = await import_actuals(req, uuid.uuid4(), mock_db)
    assert result.records_created == 2
    assert result.records_updated == 0
    assert result.validation_warnings == []


async def test_import_actuals_skips_invalid_rows() -> None:
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    mock_db.add = MagicMock()  # sync method on the session
    mock_db.commit = AsyncMock()

    req = ActualsUploadRequest(
        blueprint_id="bp_001",
        csv_content="month,revenue\n1,12000\nbad_month,15000",
        column_mapping={},
    )
    result = await import_actuals(req, uuid.uuid4(), mock_db)
    assert result.records_created == 1
    assert len(result.validation_warnings) == 1


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_import_actuals_create_then_update(db: AsyncSession) -> None:
    ws = Workspace(name="W", slug=f"w-{uuid.uuid4().hex[:8]}")
    db.add(ws)
    await db.flush()
    bp = Blueprint(name="B", industry="tech", stage="seed", workspace_id=ws.id)
    db.add(bp)
    await db.flush()
    bpv = BlueprintVersion(
        blueprint_id=bp.id, version=1, payload={"x": 1}, vulnerabilities=[]
    )
    db.add(bpv)
    await db.commit()

    # First upload creates a record.
    result = await import_actuals(
        ActualsUploadRequest(blueprint_id=bp.id, csv_content="month,revenue\n1,12000\n2,15000"),
        ws.id,
        db,
    )
    assert result.records_created == 2
    assert result.records_updated == 0

    # Second upload of month 1 with an extra column merges into the existing row.
    result2 = await import_actuals(
        ActualsUploadRequest(
            blueprint_id=bp.id,
            csv_content="month,costs\n1,14000",
        ),
        ws.id,
        db,
    )
    assert result2.records_created == 0
    assert result2.records_updated == 1

    rows = (await db.execute(select(ActualsRecord))).scalars().all()
    by_month = {r.month: r.fields for r in rows}
    assert by_month[1] == {"revenue": 12000.0, "costs": 14000.0}
