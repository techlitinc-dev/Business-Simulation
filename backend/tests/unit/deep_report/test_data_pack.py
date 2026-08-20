"""Unit tests for the deep-report data pack builder (Day 02)."""

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
from app.services.deep_report.data_pack import (
    _extract_chronicle,
    _extract_comparison_deltas,
    _extract_engine_config,
    _extract_mc_aggregates,
    _extract_run_metadata,
    _fetch_blueprint,
    _fetch_events_decisions,
    _fetch_tick_logs,
    _fetch_vulnerabilities,
    build_data_pack,
    validate_data_pack,
)
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

    bp = Blueprint(
        name="B", industry="tech", stage="seed", workspace_id=ws.id
    )
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


async def test_build_data_pack_only_fetches_declared_keys(db: AsyncSession) -> None:
    run = await _seed_run(db)

    # A section that only asks for tick logs must not pull other keys.
    pack = await build_data_pack(_sec(DataInputKey.TICK_LOGS), run.id, db)
    assert set(pack.keys()) == {"tick_logs"}
    assert len(pack["tick_logs"]) == 2
    assert pack["tick_logs"][0]["month"] == 1
    assert "revenue" in pack["tick_logs"][0]


async def test_build_data_pack_blueprint_and_vulnerabilities(
    db: AsyncSession,
) -> None:
    run = await _seed_run(db)
    pack = await build_data_pack(
        _sec(DataInputKey.BLUEPRINT, DataInputKey.FORGE_VULNERABILITIES), run.id, db
    )
    assert set(pack.keys()) == {"blueprint", "forge_vulnerabilities"}
    assert pack["blueprint"]["revenue_engine"]["streams"][0]["price_point"] == 99
    assert pack["forge_vulnerabilities"][0]["description"] == "Concentration"


async def test_build_data_pack_run_metadata_and_config(db: AsyncSession) -> None:
    run = await _seed_run(db)
    pack = await build_data_pack(
        _sec(DataInputKey.RUN_METADATA, DataInputKey.ENGINE_CONFIG), run.id, db
    )
    assert pack["run_metadata"]["run_id"] == run.id
    assert pack["run_metadata"]["seed"] == 42
    assert pack["run_metadata"]["status"] == "completed"
    assert pack["engine_config"]["n_runs"] == 20


async def test_build_data_pack_mc_aggregates(db: AsyncSession) -> None:
    run = await _seed_run(db)
    pack = await build_data_pack(_sec(DataInputKey.MC_AGGREGATES), run.id, db)
    assert pack["mc_aggregates"]["survival_rate"] == 0.75
    assert pack["mc_aggregates"]["n_runs"] == 20


async def test_build_data_pack_events_decisions(db: AsyncSession) -> None:
    run = await _seed_run(db)
    pack = await build_data_pack(_sec(DataInputKey.EVENTS_DECISIONS), run.id, db)
    assert len(pack["events_decisions"]["events"]) == 1
    assert pack["events_decisions"]["events"][0]["month"] == 3
    assert pack["events_decisions"]["decisions"][0]["option_id"] == "A"
    # Decision month is derived from its linked event.
    assert pack["events_decisions"]["decisions"][0]["month"] == 3


async def test_build_data_pack_chronicle_and_deltas(db: AsyncSession) -> None:
    run = await _seed_run(db)
    pack = await build_data_pack(
        _sec(DataInputKey.CHRONICLE, DataInputKey.COMPARISON_DELTAS), run.id, db
    )
    assert pack["chronicle"][0]["event"] == "founded"
    assert pack["comparison_deltas"]["survival_rate_pp"] == 5.0


async def test_build_data_pack_optimizations_uses_measure_all_tweaks(
    db: AsyncSession,
) -> None:
    run = await _seed_run(db)
    pack = await build_data_pack(_sec(DataInputKey.OPTIMIZATION_ENTRIES), run.id, db)
    # measure_all_tweaks over the seeded blueprint payload (deterministic).
    assert len(pack["optimization_entries"]) == 6
    keys = {t["tweak_key"] for t in pack["optimization_entries"]}
    assert "churn" in keys and "cac" in keys


async def test_build_data_pack_missing_run_returns_none(db: AsyncSession) -> None:
    await _seed_run(db)
    pack = await build_data_pack(_sec(DataInputKey.RUN_METADATA), "run_missing", db)
    assert pack["run_metadata"] is None


async def test_build_data_pack_empty_inputs(db: AsyncSession) -> None:
    run = await _seed_run(db)
    pack = await build_data_pack(_sec(), run.id, db)
    assert pack == {}


async def test_extract_mc_aggregates_ignores_non_mc_result(
    db: AsyncSession,
) -> None:
    run = await _seed_run(db)
    run.result = {"survived": False, "months_survived": 10}  # baseline shape
    assert _extract_mc_aggregates(run) is None


async def test_fetch_helpers(db: AsyncSession) -> None:
    run = await _seed_run(db)

    ticks = await _fetch_tick_logs(run.id, db)
    assert len(ticks) == 2

    blueprint = await _fetch_blueprint(run, db)
    assert blueprint is not None
    assert blueprint["revenue_engine"]["streams"][0]["price_point"] == 99

    vulnerabilities = await _fetch_vulnerabilities(run, db)
    assert vulnerabilities[0]["severity"] == "high"

    events_decisions = await _fetch_events_decisions(run.id, db)
    assert events_decisions["decisions"][0]["month"] == 3

    chronicle = _extract_chronicle(run)
    assert chronicle is not None
    assert chronicle[0]["event"] == "founded"

    deltas = _extract_comparison_deltas(run)
    assert deltas is not None
    assert deltas["survival_rate_pp"] == 5.0

    config = _extract_engine_config(run)
    assert config is not None
    assert config["months"] == 24

    metadata = _extract_run_metadata(run)
    assert metadata is not None
    assert metadata["run_id"] == run.id


def test_validate_data_pack_no_warnings() -> None:
    section = _sec(DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES)
    pack = {"tick_logs": [{"month": 1}], "mc_aggregates": {"n_runs": 20}}
    assert validate_data_pack(pack, section) == []


def test_validate_data_pack_flags_none_inputs() -> None:
    section = _sec(DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES)
    pack = {"tick_logs": [{"month": 1}], "mc_aggregates": None}
    warnings = validate_data_pack(pack, section)
    assert len(warnings) == 1
    assert "DataInputKey.MC_AGGREGATES resolved to None" in warnings[0]
    assert "section 1" in warnings[0]


def test_validate_data_pack_missing_key_flags() -> None:
    section = _sec(DataInputKey.RUN_METADATA)
    warnings = validate_data_pack({}, section)
    assert len(warnings) == 1
    assert "DataInputKey.RUN_METADATA resolved to None" in warnings[0]


async def test_build_data_pack_is_deterministic(db: AsyncSession) -> None:
    run = await _seed_run(db)
    section = _sec(DataInputKey.MC_AGGREGATES, DataInputKey.ENGINE_CONFIG)

    pack1 = await build_data_pack(section, run.id, db)
    pack2 = await build_data_pack(section, run.id, db)
    assert pack1 == pack2
