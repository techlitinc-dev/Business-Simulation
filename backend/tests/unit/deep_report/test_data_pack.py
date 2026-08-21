"""Day 02 tests: deep-report data pack builder (data_pack.py).

Covers key extraction, pack shape, serializability, validation warnings,
and determinism — all against an in-memory SQLite DB seeded with a run.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from app.db.base import Base
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.simulation import (
    Decision,
    RunStatus,
    SimulationEvent,
    SimulationRun,
    TickLog,
)
from app.models.workspace import Workspace
from app.services.deep_report.data_pack import build_data_pack, validate_data_pack
from app.services.deep_report.manifest import DataInputKey, SectionDef
from sqlalchemy.ext.asyncio import AsyncSession


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


def _sec(*keys: DataInputKey) -> SectionDef:
    return SectionDef(
        section_number=1,
        title="Test Section",
        page_budget=2,
        data_inputs=list(keys),
        prompt_template="test.md",
    )


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
_BLUEPRINT_PAYLOAD = json.loads((FIXTURES / "blueprint_golden.json").read_text())


async def _seed_run(db: AsyncSession, *, with_ticks: bool = True) -> SimulationRun:
    ws = Workspace(name="W", slug=f"w-{uuid.uuid4().hex[:8]}")
    db.add(ws)
    await db.flush()

    bp = Blueprint(name="B", industry="tech", stage="seed", workspace_id=ws.id)
    db.add(bp)
    await db.flush()
    bpv = BlueprintVersion(
        blueprint_id=bp.id,
        version=1,
        payload=_BLUEPRINT_PAYLOAD,
        vulnerabilities=[{"severity": "high", "description": "Concentration"}],
    )
    db.add(bpv)
    await db.flush()

    run = SimulationRun(
        workspace_id=ws.id,
        blueprint_version_id=bpv.id,
        mode="monte_carlo",
        status=RunStatus.COMPLETED,
        seed=42,
        config={"seed": 42, "n_runs": 20, "months": 24},
        result={
            "n_runs": 20,
            "survival_rate": 0.75,
            "runs_summary": [
                {"seed": 1, "survived": True, "lifespan_months": 24},
                {"seed": 2, "survived": False, "lifespan_months": 12},
            ],
        },
        state_snapshot={
            "chronicle": [{"month": 1, "event": "founded"}],
            "comparison_deltas": {"survival_rate_pp": 5.0},
        },
    )
    db.add(run)
    await db.flush()

    if with_ticks:
        db.add_all(
            [
                TickLog(
                    run_id=run.id,
                    month=1,
                    kpis={
                        "month": 1.0,
                        "cash_balance": 100.0,
                        "revenue": 10.0,
                        "costs": 15.0,
                        "customers": 5.0,
                        "mrr": 10.0,
                        "churn_rate": 0.05,
                        "ltv_cac_ratio": 2.0,
                    },
                ),
                TickLog(
                    run_id=run.id,
                    month=2,
                    kpis={
                        "month": 2.0,
                        "cash_balance": 90.0,
                        "revenue": 12.0,
                        "costs": 16.0,
                        "customers": 6.0,
                        "mrr": 12.0,
                        "churn_rate": 0.04,
                        "ltv_cac_ratio": 2.5,
                    },
                ),
            ]
        )
        event = SimulationEvent(
            run_id=run.id, month=3, payload={"category": "market"}, status="resolved"
        )
        db.add(event)
        await db.flush()
        db.add(
            Decision(
                run_id=run.id,
                event_id=event.id,
                option_id="A",
                projection={"cash_impact_monthly": -5000},
            )
        )
    await db.commit()
    return run


async def test_tick_logs_key_present(db: AsyncSession) -> None:
    """TICK_LOGS resolves to a list of monthly KPI rows."""
    run = await _seed_run(db)
    pack = await build_data_pack(_sec(DataInputKey.TICK_LOGS), run.id, db)
    assert isinstance(pack["tick_logs"], list)
    assert len(pack["tick_logs"]) == 2
    assert {t["month"] for t in pack["tick_logs"]} == {1, 2}
    assert "revenue" in pack["tick_logs"][0]


async def test_mc_aggregates_key_present(db: AsyncSession) -> None:
    """MC_AGGREGATES returns the stored run.result dict."""
    run = await _seed_run(db)
    pack = await build_data_pack(_sec(DataInputKey.MC_AGGREGATES), run.id, db)
    assert pack["mc_aggregates"] == run.result


async def test_run_metadata_structure(db: AsyncSession) -> None:
    """run_metadata dict contains run_id and seed."""
    run = await _seed_run(db)
    pack = await build_data_pack(_sec(DataInputKey.RUN_METADATA), run.id, db)
    metadata = pack["run_metadata"]
    assert metadata["run_id"] == run.id
    assert metadata["seed"] == 42


async def test_engine_config_returned(db: AsyncSession) -> None:
    """engine_config contains the months field."""
    run = await _seed_run(db)
    pack = await build_data_pack(_sec(DataInputKey.ENGINE_CONFIG), run.id, db)
    assert pack["engine_config"]["months"] == 24


async def test_chronicle_extracted(db: AsyncSession) -> None:
    """chronicle is a dict from state_snapshot."""
    run = await _seed_run(db)
    pack = await build_data_pack(_sec(DataInputKey.CHRONICLE), run.id, db)
    chronicle = pack["chronicle"]
    assert isinstance(chronicle, list)
    assert isinstance(chronicle[0], dict)
    assert chronicle[0]["event"] == "founded"


async def test_only_requested_keys_in_pack(db: AsyncSession) -> None:
    """Pack only has keys declared in section.data_inputs."""
    run = await _seed_run(db)
    section = _sec(DataInputKey.TICK_LOGS, DataInputKey.RUN_METADATA)
    pack = await build_data_pack(section, run.id, db)
    assert set(pack.keys()) == {k.value for k in section.data_inputs}


async def test_pack_is_serializable(db: AsyncSession) -> None:
    """json.dumps(pack) succeeds without error."""
    run = await _seed_run(db)
    section = _sec(DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES)
    pack = await build_data_pack(section, run.id, db)
    json.dumps(pack)  # must not raise


def test_no_warnings_when_complete() -> None:
    """validate_data_pack returns [] when all keys have values."""
    section = _sec(DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES)
    pack = {"tick_logs": [{"month": 1}], "mc_aggregates": {"n_runs": 20}}
    assert validate_data_pack(pack, section) == []


def test_warning_when_key_is_none() -> None:
    """validate_data_pack returns a warning for None keys."""
    section = _sec(DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES)
    pack = {"tick_logs": [{"month": 1}], "mc_aggregates": None}
    warnings = validate_data_pack(pack, section)
    assert len(warnings) == 1
    assert "DataInputKey.MC_AGGREGATES resolved to None" in warnings[0]


async def test_deterministic_same_inputs_same_output(db: AsyncSession) -> None:
    """Calling build_data_pack twice with same inputs returns identical dict."""
    run = await _seed_run(db)
    section = _sec(DataInputKey.MC_AGGREGATES, DataInputKey.ENGINE_CONFIG)

    pack1 = await build_data_pack(section, run.id, db)
    pack2 = await build_data_pack(section, run.id, db)
    assert pack1 == pack2
