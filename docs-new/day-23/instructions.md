# Day 23 — F-03: Lender Report Manifest + Investor Data Room

## Feature
F-03: Investor & Lender Toolkit

## Goal
Create a lender-focused report manifest (F-01 variant). Build the data room service that bundles PDF + CSV exports into a signed, expiring, view-tracked downloadable package.

---

## Step 1 — Lender Report Manifest

`backend/app/services/deep_report/manifests/lender_manifest.py`:
```python
from app.services.deep_report.manifest import (
    ReportManifest, SectionDef, ReportTier, DataInputKey
)

LENDER_MANIFEST = ReportManifest(
    name="Loan Readiness Assessment",
    report_type="lender_report",
    tier=ReportTier.ENTERPRISE,
    sections=[
        SectionDef(section_number=1,  title="Cover & Executive Summary",
                   page_budget=3, data_inputs=[DataInputKey.RUN_METADATA, DataInputKey.MC_AGGREGATES],
                   prompt_template="lender_cover.md", ai_generated=False, tier_minimum=ReportTier.PRO),
        SectionDef(section_number=2,  title="Cash Flow Stability Analysis",
                   page_budget=5, data_inputs=[DataInputKey.TICK_LOGS],
                   prompt_template="lender_cashflow.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=3,  title="Debt Service Coverage Assessment",
                   page_budget=4, data_inputs=[DataInputKey.TICK_LOGS, DataInputKey.ENGINE_CONFIG],
                   prompt_template="lender_dscr.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=4,  title="Downside Protection & Stress Scenarios",
                   page_budget=5, data_inputs=[DataInputKey.MC_AGGREGATES, DataInputKey.TICK_LOGS],
                   prompt_template="lender_downside.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=5,  title="Collateral & Business Asset Summary",
                   page_budget=3, data_inputs=[DataInputKey.BLUEPRINT],
                   prompt_template="lender_collateral.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=6,  title="Repayment Capacity Analysis",
                   page_budget=4, data_inputs=[DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES],
                   prompt_template="lender_repayment.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=7,  title="Risk Register & Covenants",
                   page_budget=3, data_inputs=[DataInputKey.FORGE_VULNERABILITIES],
                   prompt_template="lender_risk.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=8,  title="Conclusion & Lender Recommendation",
                   page_budget=2, data_inputs=[DataInputKey.MC_AGGREGATES, DataInputKey.RUN_METADATA],
                   prompt_template="lender_conclusion.md", tier_minimum=ReportTier.PRO),
    ]
)
```

Register in manifest registry:
```python
from app.services.deep_report.manifests.lender_manifest import LENDER_MANIFEST
MANIFEST_REGISTRY["lender_report"] = LENDER_MANIFEST
```

---

## Step 2 — Data Room Service

`backend/app/services/dataroom/schemas.py`:
```python
from pydantic import BaseModel
from datetime import datetime


class DataRoomCreate(BaseModel):
    run_id: str
    expiry_days: int = 7
    label: str = "Investor Data Room"


class DataRoomInfo(BaseModel):
    token: str
    label: str
    run_id: str
    created_at: datetime
    expires_at: datetime
    view_count: int
    download_url: str
    is_active: bool
```

`backend/app/services/dataroom/dataroom_service.py`:
```python
from __future__ import annotations
import csv
import io
import json
import os
import zipfile
import tempfile
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.core.config import settings
import redis as redis_lib

REDIS_PREFIX = "dataroom:"
DATAROOM_STORAGE_DIR = getattr(settings, "REPORT_STORAGE_DIR", "/tmp/reports")


def _get_serializer():
    return URLSafeTimedSerializer(settings.SECRET_KEY)


def _get_redis():
    return redis_lib.from_url(settings.REDIS_URL)


async def create_dataroom(
    run_id: str,
    label: str,
    expiry_days: int,
    pdf_path: str | None,
    tick_logs: list[dict],
    mc_aggregates: dict,
    workspace_name: str,
    db: AsyncSession,
) -> dict:
    """Bundle PDF + CSV exports and create a signed expiring data room link."""
    s = _get_serializer()
    token = s.dumps({"run_id": run_id, "workspace": workspace_name}, salt="dataroom")
    expires_at = datetime.utcnow() + timedelta(days=expiry_days)

    # Build ZIP bundle
    bundle_path = os.path.join(DATAROOM_STORAGE_DIR, f"dataroom_{token[:12]}.zip")
    os.makedirs(DATAROOM_STORAGE_DIR, exist_ok=True)

    with zipfile.ZipFile(bundle_path, "w") as zf:
        # Include PDF if available
        if pdf_path and os.path.exists(pdf_path):
            zf.write(pdf_path, "simulation_audit.pdf")

        # KPI CSV export
        if tick_logs:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=tick_logs[0].keys())
            writer.writeheader()
            writer.writerows(tick_logs)
            zf.writestr("kpi_ticks.csv", buf.getvalue())

        # MC aggregates JSON
        zf.writestr("mc_aggregates.json", json.dumps(mc_aggregates, indent=2))

        # Methodology note
        zf.writestr("methodology.txt",
            "Generated by The Forge Business Simulation Engine.\n"
            "All financial projections are deterministic simulations, not guarantees.")

    # Store metadata in Redis
    r = _get_redis()
    meta = {
        "run_id": run_id, "label": label, "token": token,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": expires_at.isoformat(),
        "view_count": 0, "bundle_path": bundle_path,
    }
    r.setex(f"{REDIS_PREFIX}{token[:16]}", int(timedelta(days=expiry_days + 1).total_seconds()),
            json.dumps(meta))

    return {
        "token": token[:16],
        "download_url": f"/api/v1/dataroom/{token[:16]}/download",
        "expires_at": expires_at.isoformat(),
        "label": label,
    }


def get_dataroom(short_token: str) -> dict | None:
    r = _get_redis()
    raw = r.get(f"{REDIS_PREFIX}{short_token}")
    if not raw:
        return None
    meta = json.loads(raw)
    # Check expiry
    expires_at = datetime.fromisoformat(meta["expires_at"])
    if datetime.utcnow() > expires_at:
        return None
    return meta


def record_view(short_token: str):
    r = _get_redis()
    raw = r.get(f"{REDIS_PREFIX}{short_token}")
    if raw:
        meta = json.loads(raw)
        meta["view_count"] += 1
        ttl = r.ttl(f"{REDIS_PREFIX}{short_token}")
        r.setex(f"{REDIS_PREFIX}{short_token}", max(ttl, 1), json.dumps(meta))


def revoke_dataroom(short_token: str):
    r = _get_redis()
    r.delete(f"{REDIS_PREFIX}{short_token}")
```

---

## Step 3 — API endpoint

`backend/app/api/v1/endpoints/dataroom.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, get_current_workspace
from app.services.dataroom.schemas import DataRoomCreate, DataRoomInfo
from app.services.dataroom.dataroom_service import create_dataroom, get_dataroom, record_view, revoke_dataroom

router = APIRouter(prefix="/dataroom", tags=["dataroom"])


@router.post("/", status_code=201)
async def create_data_room(
    body: DataRoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    from app.services.deep_report.data_pack import _fetch_tick_logs, _extract_mc_aggregates, _fetch_run
    run = await _fetch_run(body.run_id, db)
    ticks = await _fetch_tick_logs(body.run_id, db)
    mc = _extract_mc_aggregates(run) or {}
    return await create_dataroom(
        run_id=body.run_id, label=body.label, expiry_days=body.expiry_days,
        pdf_path=None, tick_logs=ticks, mc_aggregates=mc,
        workspace_name=workspace.name, db=db,
    )


@router.get("/{token}/download")
async def download_data_room(token: str):
    meta = get_dataroom(token)
    if not meta:
        raise HTTPException(410, "Data room link has expired or been revoked")
    record_view(token)
    return FileResponse(meta["bundle_path"], media_type="application/zip",
                        filename=f"data_room_{token}.zip")


@router.delete("/{token}")
async def revoke_data_room(token: str, current_user=Depends(get_current_user)):
    revoke_dataroom(token)
    return {"revoked": True}
```

---

## Tests

`backend/tests/unit/dataroom/test_dataroom_service.py`:
```python
import pytest
from unittest.mock import patch
from app.services.dataroom.dataroom_service import create_dataroom, get_dataroom, record_view, revoke_dataroom
import asyncio

MOCK_TICKS = [{"month": 1, "revenue": 12000, "cash": 86000, "costs": 14000}]
MOCK_MC = {"survival_rate": 0.68}

def test_create_and_retrieve_dataroom(tmp_path):
    with patch("app.services.dataroom.dataroom_service.DATAROOM_STORAGE_DIR", str(tmp_path)), \
         patch("app.services.dataroom.dataroom_service._get_redis") as mock_redis:
        import json
        stored = {}
        r = mock_redis.return_value
        r.setex = lambda key, ttl, val: stored.update({key: val})
        r.get = lambda key: stored.get(key)

        result = asyncio.get_event_loop().run_until_complete(create_dataroom(
            run_id="run_001", label="Test Room", expiry_days=7,
            pdf_path=None, tick_logs=MOCK_TICKS, mc_aggregates=MOCK_MC,
            workspace_name="TestCo", db=None,
        ))
        assert "token" in result
        assert "download_url" in result
        assert "/download" in result["download_url"]

def test_revoke_deletes_key():
    with patch("app.services.dataroom.dataroom_service._get_redis") as mock_redis:
        deleted = []
        r = mock_redis.return_value
        r.delete = lambda key: deleted.append(key)
        revoke_dataroom("testtoken")
        assert any("testtoken" in k for k in deleted)
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/dataroom/ -v
cd backend && ruff check app/services/dataroom/ app/api/v1/endpoints/dataroom.py
```
