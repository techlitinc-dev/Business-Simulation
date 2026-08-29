# Day 02 — F-01: Deterministic Data Pack Assembly

## Feature
F-01: Deep-Dive Report Engine

## Goal
Flesh out `build_data_pack()` so every section's required inputs are pulled from the real database — tick logs, MC aggregates, Forge vulnerabilities, optimization entries, chronicle, comparison deltas, run metadata, and engine config. All outputs must be deterministic (same run_id → same dict), serializable, and contain zero fabricated numbers.

## Prerequisites
- Day 01 complete (`manifest.py`, `data_pack.py` stub, `registry.py`)
- Existing services: `report_service.py`, `optimization_service.py`, `simulation_service.py`
- Existing models: `SimulationRun`, `TickLog`, `SimulationEvent`, `Decision`, `Report`, `Blueprint`, `BlueprintVersion`

---

## Step 1 — Flesh out `data_pack.py`

Replace the stub in `backend/app/services/deep_report/data_pack.py`:

```python
from __future__ import annotations
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import SimulationRun, TickLog, SimulationEvent, Decision
from app.models.report import Report
from app.models.blueprint import Blueprint, BlueprintVersion
from app.services.deep_report.manifest import SectionDef, DataInputKey
from app.services.optimization_service import measure_all_tweaks
from app.engine.metrics import resilience_score


async def build_data_pack(
    section: SectionDef,
    run_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Assemble the deterministic data pack for a single section.
    Only fetches the data keys declared in section.data_inputs.
    All numbers come from the engine or stored tick data — never fabricated.
    """
    pack: dict[str, Any] = {}

    # Fetch the run once if any run-dependent key is needed
    run = None
    run_dependent = {
        DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES,
        DataInputKey.EVENTS_DECISIONS, DataInputKey.CHRONICLE,
        DataInputKey.OPTIMIZATION_ENTRIES, DataInputKey.COMPARISON_DELTAS,
        DataInputKey.RUN_METADATA, DataInputKey.ENGINE_CONFIG,
    }
    if any(k in run_dependent for k in section.data_inputs):
        run = await _fetch_run(run_id, db)

    for key in section.data_inputs:
        if key == DataInputKey.BLUEPRINT:
            pack[key.value] = await _fetch_blueprint(run, db)
        elif key == DataInputKey.TICK_LOGS:
            pack[key.value] = await _fetch_tick_logs(run_id, db)
        elif key == DataInputKey.MC_AGGREGATES:
            pack[key.value] = _extract_mc_aggregates(run)
        elif key == DataInputKey.FORGE_VULNERABILITIES:
            pack[key.value] = await _fetch_vulnerabilities(run, db)
        elif key == DataInputKey.OPTIMIZATION_ENTRIES:
            pack[key.value] = await _fetch_optimizations(run, db)
        elif key == DataInputKey.CHRONICLE:
            pack[key.value] = _extract_chronicle(run)
        elif key == DataInputKey.COMPARISON_DELTAS:
            pack[key.value] = _extract_comparison_deltas(run)
        elif key == DataInputKey.RUN_METADATA:
            pack[key.value] = _extract_run_metadata(run)
        elif key == DataInputKey.ENGINE_CONFIG:
            pack[key.value] = _extract_engine_config(run)
        elif key == DataInputKey.EVENTS_DECISIONS:
            pack[key.value] = await _fetch_events_decisions(run_id, db)

    return pack


# ── Private helpers ──────────────────────────────────────────────────────────

async def _fetch_run(run_id: str, db: AsyncSession) -> SimulationRun | None:
    result = await db.execute(select(SimulationRun).where(SimulationRun.id == run_id))
    return result.scalar_one_or_none()


async def _fetch_blueprint(run: SimulationRun | None, db: AsyncSession) -> dict | None:
    if run is None:
        return None
    result = await db.execute(
        select(BlueprintVersion).where(BlueprintVersion.id == run.blueprint_version_id)
    )
    bpv = result.scalar_one_or_none()
    return bpv.payload if bpv else None


async def _fetch_tick_logs(run_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(TickLog).where(TickLog.run_id == run_id).order_by(TickLog.month)
    )
    ticks = result.scalars().all()
    return [
        {
            "month": t.month,
            "revenue": t.revenue,
            "costs": t.costs,
            "cash": t.cash,
            "customers": t.customers,
            "mrr": t.mrr,
            "runway_months": t.runway_months,
            "ltv_cac_ratio": t.ltv_cac_ratio,
            "churn_rate": t.churn_rate,
        }
        for t in ticks
    ]


def _extract_mc_aggregates(run: SimulationRun | None) -> dict | None:
    if run is None or run.mc_result is None:
        return None
    return run.mc_result  # already stored as JSONB


async def _fetch_vulnerabilities(run: SimulationRun | None, db: AsyncSession) -> list[dict]:
    if run is None:
        return []
    result = await db.execute(
        select(BlueprintVersion).where(BlueprintVersion.id == run.blueprint_version_id)
    )
    bpv = result.scalar_one_or_none()
    if bpv is None:
        return []
    return bpv.vulnerabilities or []


async def _fetch_optimizations(run: SimulationRun | None, db: AsyncSession) -> list[dict]:
    if run is None:
        return []
    # Re-use the optimization service (deterministic; same seed → same result)
    from app.services.optimization_service import measure_all_tweaks
    tweaks = await measure_all_tweaks(run.id, db)
    return [t.model_dump() for t in tweaks]


def _extract_chronicle(run: SimulationRun | None) -> dict | None:
    if run is None:
        return None
    return run.state_snapshot.get("chronicle") if run.state_snapshot else None


def _extract_comparison_deltas(run: SimulationRun | None) -> dict | None:
    if run is None:
        return None
    return run.state_snapshot.get("comparison_deltas") if run.state_snapshot else None


def _extract_run_metadata(run: SimulationRun | None) -> dict | None:
    if run is None:
        return None
    return {
        "run_id": run.id,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "status": run.status.value if run.status else None,
        "config": run.config,
        "seed": run.config.get("seed") if run.config else None,
    }


def _extract_engine_config(run: SimulationRun | None) -> dict | None:
    if run is None:
        return None
    return run.config


async def _fetch_events_decisions(run_id: str, db: AsyncSession) -> dict:
    events_result = await db.execute(
        select(SimulationEvent).where(SimulationEvent.run_id == run_id).order_by(SimulationEvent.month)
    )
    decisions_result = await db.execute(
        select(Decision).where(Decision.run_id == run_id).order_by(Decision.month)
    )
    events = events_result.scalars().all()
    decisions = decisions_result.scalars().all()
    return {
        "events": [{"month": e.month, "type": e.event_type, "payload": e.payload} for e in events],
        "decisions": [{"month": d.month, "option_id": d.option_id, "outcome_delta": d.outcome_delta} for d in decisions],
    }
```

---

## Step 2 — Add a `validate_data_pack` helper

Add to `data_pack.py`:

```python
def validate_data_pack(pack: dict[str, Any], section: SectionDef) -> list[str]:
    """
    Returns a list of warning strings for any declared input that resolved to None.
    Empty list = pack is complete.
    """
    warnings = []
    for key in section.data_inputs:
        value = pack.get(key.value)
        if value is None:
            warnings.append(f"DataInputKey.{key.name} resolved to None for section {section.section_number}")
    return warnings
```

---

## Step 3 — Unit test file

Create `backend/tests/unit/deep_report/test_data_pack.py`:

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.deep_report.data_pack import build_data_pack, validate_data_pack
from app.services.deep_report.manifest import SectionDef, DataInputKey


def _make_section(*keys: DataInputKey) -> SectionDef:
    return SectionDef(
        section_number=1,
        title="Test Section",
        page_budget=2,
        data_inputs=list(keys),
        prompt_template="test.md",
    )


@pytest.fixture
def mock_run():
    run = MagicMock()
    run.id = "run_test_001"
    run.blueprint_version_id = "bpv_001"
    run.mc_result = {"survival_rate": 0.72, "median_lifespan": 18}
    run.config = {"seed": 42, "months": 24}
    run.state_snapshot = {
        "chronicle": {"entries": []},
        "comparison_deltas": {},
    }
    run.created_at = None
    run.status = MagicMock(value="completed")
    return run


@pytest.fixture
def mock_db(mock_run):
    db = AsyncMock()
    # Simulate DB returning the mock run
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_run
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)
    return db


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestBuildDataPack:

    def test_tick_logs_key_present(self, mock_db):
        section = _make_section(DataInputKey.TICK_LOGS)
        pack = run_async(build_data_pack(section, "run_test_001", mock_db))
        assert "tick_logs" in pack
        assert isinstance(pack["tick_logs"], list)

    def test_mc_aggregates_key_present(self, mock_db, mock_run):
        section = _make_section(DataInputKey.MC_AGGREGATES)
        pack = run_async(build_data_pack(section, "run_test_001", mock_db))
        assert "mc_aggregates" in pack
        assert pack["mc_aggregates"]["survival_rate"] == 0.72

    def test_run_metadata_structure(self, mock_db, mock_run):
        section = _make_section(DataInputKey.RUN_METADATA)
        pack = run_async(build_data_pack(section, "run_test_001", mock_db))
        meta = pack["run_metadata"]
        assert meta["run_id"] == "run_test_001"
        assert meta["seed"] == 42

    def test_engine_config_returned(self, mock_db):
        section = _make_section(DataInputKey.ENGINE_CONFIG)
        pack = run_async(build_data_pack(section, "run_test_001", mock_db))
        assert pack["engine_config"]["months"] == 24

    def test_chronicle_extracted(self, mock_db):
        section = _make_section(DataInputKey.CHRONICLE)
        pack = run_async(build_data_pack(section, "run_test_001", mock_db))
        assert "chronicle" in pack
        assert isinstance(pack["chronicle"], dict)

    def test_only_requested_keys_in_pack(self, mock_db):
        section = _make_section(DataInputKey.TICK_LOGS, DataInputKey.RUN_METADATA)
        pack = run_async(build_data_pack(section, "run_test_001", mock_db))
        assert set(pack.keys()) == {"tick_logs", "run_metadata"}

    def test_pack_is_serializable(self, mock_db):
        import json
        section = _make_section(DataInputKey.MC_AGGREGATES, DataInputKey.ENGINE_CONFIG)
        pack = run_async(build_data_pack(section, "run_test_001", mock_db))
        serialized = json.dumps(pack, default=str)
        assert isinstance(serialized, str)


class TestValidateDataPack:

    def test_no_warnings_when_complete(self):
        section = _make_section(DataInputKey.TICK_LOGS)
        pack = {"tick_logs": [{"month": 1}]}
        assert validate_data_pack(pack, section) == []

    def test_warning_when_key_is_none(self):
        section = _make_section(DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES)
        pack = {"tick_logs": [], "mc_aggregates": None}
        warnings = validate_data_pack(pack, section)
        assert len(warnings) == 1
        assert "MC_AGGREGATES" in warnings[0]

    def test_deterministic_same_inputs_same_output(self, mock_db):
        section = _make_section(DataInputKey.ENGINE_CONFIG)
        pack1 = run_async(build_data_pack(section, "run_test_001", mock_db))
        pack2 = run_async(build_data_pack(section, "run_test_001", mock_db))
        assert pack1 == pack2
```

---

## Verification Commands

```bash
cd backend && pytest tests/unit/deep_report/test_data_pack.py -v
cd backend && ruff check app/services/deep_report/data_pack.py
cd backend && mypy app/services/deep_report/data_pack.py --ignore-missing-imports
```
