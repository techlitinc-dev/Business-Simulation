"""Unit tests for the actuals CSV importer (Day 12)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.services.actuals.importer import _parse_csv, _validate_row, import_actuals
from app.services.actuals.schemas import ActualsUploadRequest

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


async def test_import_actuals_unmapped_columns() -> None:
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    mock_db.add = MagicMock()  # sync method on the session
    mock_db.commit = AsyncMock()

    req = ActualsUploadRequest(
        blueprint_id="bp_001",
        csv_content="month,revenue,extra_col\n1,12000,foo\n2,15000,bar",
        column_mapping={},
    )
    result = await import_actuals(req, uuid.uuid4(), mock_db)
    assert "extra_col" in result.unmapped_columns
    assert result.records_created == 2
    assert result.validation_warnings == []

