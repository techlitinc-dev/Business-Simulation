# Day 10 — F-06: What-If API + Save as Blueprint Version

## Feature
F-06: What-If Lab & Sensitivity Sweeps

## Goal
Expose the sweep and break-even logic as REST endpoints. Add `POST /whatif/save-version` that forks the current blueprint as a new `BlueprintVersion` with one parameter overridden.

## Prerequisites
- Day 08–09 complete
- `blueprint_service.py` has versioning (T17)
- `billing_service.py` / `plans.py` for plan gating (Pro+ only)

---

## Step 1 — Create `backend/app/schemas/whatif.py`

```python
from pydantic import BaseModel
from app.services.whatif.schemas import SweepRequest, SweepResult, BreakevenRequest, BreakevenResult


class SaveVersionRequest(BaseModel):
    blueprint_id: str
    param: str
    value: float
    version_label: str = "What-If Override"
```

---

## Step 2 — Create `backend/app/api/v1/endpoints/whatif.py`

```python
from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace, get_db
from app.services.whatif.schemas import SweepRequest, SweepResult, BreakevenRequest, BreakevenResult
from app.services.whatif.sweep import run_sweep
from app.services.whatif.breakeven import find_breakeven
from app.schemas.whatif import SaveVersionRequest
from app.services.blueprint_service import create_version_from_override

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatif", tags=["whatif"])


@router.post("/sweep", response_model=SweepResult)
async def sweep_endpoint(
    body: SweepRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    """
    Run a parameter sweep across a range.
    Pro+ plan required.
    """
    _require_pro(workspace)
    return await run_sweep(body, db)


@router.post("/breakeven", response_model=BreakevenResult)
async def breakeven_endpoint(
    body: BreakevenRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    """Find the parameter threshold where survival crosses 50%."""
    _require_pro(workspace)
    return await find_breakeven(body, db)


@router.post("/save-version", status_code=201)
async def save_version_endpoint(
    body: SaveVersionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    """
    Fork a blueprint version with one parameter override applied.
    Returns the new BlueprintVersion id.
    """
    _require_pro(workspace)
    new_version = await create_version_from_override(
        blueprint_id=body.blueprint_id,
        param=body.param,
        value=body.value,
        label=body.version_label,
        db=db,
        workspace_id=workspace.id,
    )
    return {"blueprint_version_id": new_version.id, "label": new_version.label}


def _require_pro(workspace):
    plan = getattr(workspace, "plan", "free")
    if plan == "free":
        raise HTTPException(status_code=402, detail="Pro plan required for What-If Lab")
```

---

## Step 3 — Add `create_version_from_override` to `blueprint_service.py`

```python
async def create_version_from_override(
    blueprint_id: str,
    param: str,
    value: float,
    label: str,
    db: AsyncSession,
    workspace_id: str,
) -> BlueprintVersion:
    """
    Fetch the latest BlueprintVersion for blueprint_id,
    deep-copy its payload, apply the parameter override,
    and insert a new BlueprintVersion row.
    """
    from app.services.whatif.sweep import _patch_payload
    from app.models.blueprint import BlueprintVersion
    import uuid, copy

    # Get latest version
    result = await db.execute(
        select(BlueprintVersion)
        .where(BlueprintVersion.blueprint_id == blueprint_id)
        .order_by(BlueprintVersion.created_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    patched_payload = _patch_payload(latest.payload, param, value)
    new_version = BlueprintVersion(
        id=f"bpv_{uuid.uuid4().hex[:12]}",
        blueprint_id=blueprint_id,
        payload=patched_payload,
        label=label,
        vulnerabilities=[],
    )
    db.add(new_version)
    await db.commit()
    await db.refresh(new_version)
    return new_version
```

---

## Step 4 — Register router

In `backend/app/api/v1/router.py`:
```python
from app.api.v1.endpoints.whatif import router as whatif_router
api_router.include_router(whatif_router)
```

---

## Step 5 — Integration tests

`backend/tests/integration/test_whatif_api.py`:

```python
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_sweep_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/whatif/sweep", json={
            "blueprint_id": "bp_001", "param": "monthly_churn",
            "min_value": 0.02, "max_value": 0.12, "steps": 3
        })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sweep_returns_result(auth_headers_pro, blueprint_fixture):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/whatif/sweep",
            json={"blueprint_id": blueprint_fixture.id, "param": "monthly_churn",
                  "min_value": 0.02, "max_value": 0.12, "steps": 3, "mc_runs": 5},
            headers=auth_headers_pro)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["grid"]) == 3
    assert 0.0 <= data["grid"][0]["survival_rate"] <= 1.0


@pytest.mark.asyncio
async def test_save_version_creates_new_version(auth_headers_pro, blueprint_fixture):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/whatif/save-version",
            json={"blueprint_id": blueprint_fixture.id, "param": "monthly_churn",
                  "value": 0.06, "version_label": "Test Override"},
            headers=auth_headers_pro)
    assert resp.status_code == 201
    data = resp.json()
    assert data["blueprint_version_id"].startswith("bpv_")
    assert data["label"] == "Test Override"


@pytest.mark.asyncio
async def test_free_plan_sweep_returns_402(auth_headers_free, blueprint_fixture):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/whatif/sweep",
            json={"blueprint_id": blueprint_fixture.id, "param": "monthly_churn",
                  "min_value": 0.02, "max_value": 0.12, "steps": 3},
            headers=auth_headers_free)
    assert resp.status_code == 402
```

---

## Verification Commands
```bash
cd backend && pytest tests/integration/test_whatif_api.py -v
cd backend && ruff check app/api/v1/endpoints/whatif.py app/schemas/whatif.py
```
