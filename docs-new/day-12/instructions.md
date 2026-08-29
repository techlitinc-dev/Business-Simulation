# Day 12 — F-04: Actuals Import Service + DB Model

## Feature
F-04: Living Blueprint & Plan-vs-Actuals

## Goal
Allow users to upload monthly actuals via CSV. Parse, validate, map columns onto blueprint fields, and persist as `ActualsRecord` rows in the database.

## Prerequisites
- Existing `Blueprint`, `BlueprintVersion` models
- Alembic for migrations
- `pandas` or `csv` stdlib (use stdlib — no new deps)

---

## Step 1 — DB Model

`backend/app/models/actuals.py`:
```python
from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class ActualsRecord(Base):
    __tablename__ = "actuals_records"

    id = Column(String, primary_key=True, default=lambda: f"act_{uuid.uuid4().hex[:12]}")
    blueprint_id = Column(String, ForeignKey("blueprints.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    month = Column(Integer, nullable=False)          # 1-based month index
    period_label = Column(String, nullable=True)     # e.g. "2024-01"
    fields = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

---

## Step 2 — Alembic migration

Create `backend/alembic/versions/xxxx_actuals_table.py`:
```python
"""add actuals_records table
Revision ID: g8h9i0j1k2l3
Revises: f7a8b9c0d1e2
"""
from alembic import op
import sqlalchemy as sa

revision = 'g8h9i0j1k2l3'
down_revision = 'f7a8b9c0d1e2'


def upgrade():
    op.create_table(
        'actuals_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('blueprint_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('period_label', sa.String(), nullable=True),
        sa.Column('fields', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['blueprint_id'], ['blueprints.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_actuals_blueprint_id', 'actuals_records', ['blueprint_id'])
    op.create_index('ix_actuals_workspace_id', 'actuals_records', ['workspace_id'])


def downgrade():
    op.drop_table('actuals_records')
```

---

## Step 3 — Actuals schemas

`backend/app/services/actuals/__init__.py` — empty

`backend/app/services/actuals/schemas.py`:
```python
from pydantic import BaseModel, Field
from typing import Any


REQUIRED_COLUMNS = ["month"]
OPTIONAL_COLUMNS = ["revenue", "costs", "cash", "customers", "churn_rate", "cac", "headcount", "mrr"]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS


class ActualsUploadRequest(BaseModel):
    blueprint_id: str
    csv_content: str = Field(..., description="Raw CSV string")
    column_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Maps CSV column names to blueprint field names. E.g. {'Monthly Revenue': 'revenue'}"
    )


class ActualsRowValidation(BaseModel):
    row: int
    errors: list[str]


class ActualsUploadResult(BaseModel):
    records_created: int
    records_updated: int
    validation_warnings: list[ActualsRowValidation]
    unmapped_columns: list[str]
```

---

## Step 4 — Importer service

`backend/app/services/actuals/importer.py`:
```python
from __future__ import annotations
import csv
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.actuals import ActualsRecord
from app.services.actuals.schemas import (
    ActualsUploadRequest, ActualsUploadResult, ActualsRowValidation, ALL_COLUMNS
)


def _parse_csv(csv_content: str, column_mapping: dict[str, str]) -> list[dict]:
    """Parse CSV string into list of dicts using column_mapping."""
    reader = csv.DictReader(io.StringIO(csv_content.strip()))
    rows = []
    for row in reader:
        mapped = {}
        for csv_col, value in row.items():
            target = column_mapping.get(csv_col, csv_col.lower().replace(" ", "_"))
            mapped[target] = value
        rows.append(mapped)
    return rows


def _validate_row(row: dict, row_num: int) -> ActualsRowValidation:
    errors = []
    if "month" not in row or not str(row["month"]).strip().isdigit():
        errors.append("'month' column must be a positive integer")
    for field in ALL_COLUMNS:
        if field in row and field != "month":
            try:
                float(row[field])
            except (ValueError, TypeError):
                errors.append(f"Field '{field}' must be numeric, got: {row[field]!r}")
    return ActualsRowValidation(row=row_num, errors=errors)


async def import_actuals(
    request: ActualsUploadRequest,
    workspace_id: str,
    db: AsyncSession,
) -> ActualsUploadResult:
    rows = _parse_csv(request.csv_content, request.column_mapping)
    warnings: list[ActualsRowValidation] = []
    created = 0
    updated = 0

    # Find columns in CSV that don't map to any known field
    unmapped = [c for c in rows[0].keys() if c not in ALL_COLUMNS] if rows else []

    for i, row in enumerate(rows, start=2):  # row 2 = first data row (row 1 = header)
        validation = _validate_row(row, i)
        if validation.errors:
            warnings.append(validation)
            continue

        month = int(row["month"])
        fields = {k: float(v) for k, v in row.items()
                  if k in ALL_COLUMNS and k != "month" and v.strip()}

        # Check if record exists
        result = await db.execute(
            select(ActualsRecord).where(
                ActualsRecord.blueprint_id == request.blueprint_id,
                ActualsRecord.workspace_id == workspace_id,
                ActualsRecord.month == month,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.fields = {**existing.fields, **fields}
            updated += 1
        else:
            record = ActualsRecord(
                blueprint_id=request.blueprint_id,
                workspace_id=workspace_id,
                month=month,
                fields=fields,
            )
            db.add(record)
            created += 1

    await db.commit()
    return ActualsUploadResult(
        records_created=created,
        records_updated=updated,
        validation_warnings=warnings,
        unmapped_columns=unmapped,
    )
```

---

## Step 5 — Tests

`backend/tests/unit/actuals/test_importer.py`:
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.actuals.importer import _parse_csv, _validate_row, import_actuals
from app.services.actuals.schemas import ActualsUploadRequest


SAMPLE_CSV = """month,revenue,costs,cash,churn_rate
1,12000,14000,86000,0.05
2,15000,14200,86800,0.04
3,invalid,14500,89000,0.04
"""


def test_parse_csv_basic():
    rows = _parse_csv(SAMPLE_CSV, {})
    assert len(rows) == 3
    assert rows[0]["month"] == "1"
    assert rows[0]["revenue"] == "12000"


def test_parse_csv_with_column_mapping():
    csv = "Month,Monthly Revenue\n1,12000\n2,15000"
    rows = _parse_csv(csv, {"Month": "month", "Monthly Revenue": "revenue"})
    assert rows[0]["month"] == "1"
    assert rows[0]["revenue"] == "12000"


def test_validate_row_valid():
    row = {"month": "1", "revenue": "12000", "costs": "14000"}
    result = _validate_row(row, 2)
    assert result.errors == []


def test_validate_row_missing_month():
    row = {"revenue": "12000"}
    result = _validate_row(row, 2)
    assert any("month" in e for e in result.errors)


def test_validate_row_invalid_number():
    row = {"month": "1", "revenue": "not_a_number"}
    result = _validate_row(row, 2)
    assert any("revenue" in e for e in result.errors)


def test_import_actuals_created_count():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    req = ActualsUploadRequest(
        blueprint_id="bp_001",
        csv_content="month,revenue\n1,12000\n2,15000",
        column_mapping={}
    )
    result = asyncio.get_event_loop().run_until_complete(
        import_actuals(req, "ws_001", mock_db)
    )
    assert result.records_created == 2
    assert result.records_updated == 0
    assert result.validation_warnings == []


def test_import_actuals_skips_invalid_rows():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    req = ActualsUploadRequest(
        blueprint_id="bp_001",
        csv_content="month,revenue\n1,12000\nbad_month,15000",
        column_mapping={}
    )
    result = asyncio.get_event_loop().run_until_complete(
        import_actuals(req, "ws_001", mock_db)
    )
    assert result.records_created == 1
    assert len(result.validation_warnings) == 1
```

---

## Verification Commands
```bash
cd backend && alembic upgrade head
cd backend && pytest tests/unit/actuals/test_importer.py -v
cd backend && ruff check app/services/actuals/ app/models/actuals.py
```
