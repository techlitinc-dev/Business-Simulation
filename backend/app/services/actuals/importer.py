from __future__ import annotations

import csv
import io
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actuals import ActualsRecord
from app.services.actuals.schemas import (
    ALL_COLUMNS,
    ActualsRowValidation,
    ActualsUploadRequest,
    ActualsUploadResult,
)


def _parse_csv(
    csv_content: str, column_mapping: dict[str, str]
) -> list[dict[str, str]]:
    """Parse CSV string into list of dicts using column_mapping."""
    reader = csv.DictReader(io.StringIO(csv_content.strip()))
    rows: list[dict[str, str]] = []
    for row in reader:
        mapped: dict[str, str] = {}
        for csv_col, value in row.items():
            target = column_mapping.get(csv_col, csv_col.lower().replace(" ", "_"))
            mapped[target] = value
        rows.append(mapped)
    return rows


def _validate_row(row: dict[str, str], row_num: int) -> ActualsRowValidation:
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
    workspace_id: uuid.UUID,
    db: AsyncSession,
) -> ActualsUploadResult:
    rows = _parse_csv(request.csv_content, request.column_mapping)
    warnings: list[ActualsRowValidation] = []
    created = 0
    updated = 0

    # Find columns in CSV that don't map to any known field.
    unmapped = [c for c in rows[0] if c not in ALL_COLUMNS] if rows else []

    for i, row in enumerate(rows, start=2):  # row 2 = first data row (row 1 = header)
        validation = _validate_row(row, i)
        if validation.errors:
            warnings.append(validation)
            continue

        month = int(row["month"])
        fields = {
            k: float(v)
            for k, v in row.items()
            if k in ALL_COLUMNS and k != "month" and v.strip()
        }

        # Check if record exists.
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
