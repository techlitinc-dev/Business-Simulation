from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blueprint import BlueprintVersion
from app.models.simulation import Decision, SimulationEvent, SimulationRun, TickLog
from app.services.deep_report.manifest import DataInputKey, SectionDef

#: Keys whose fetch needs the run row loaded first.
_RUN_DEPENDENT_KEYS = {
    DataInputKey.BLUEPRINT,
    DataInputKey.TICK_LOGS,
    DataInputKey.MC_AGGREGATES,
    DataInputKey.FORGE_VULNERABILITIES,
    DataInputKey.EVENTS_DECISIONS,
    DataInputKey.CHRONICLE,
    DataInputKey.OPTIMIZATION_ENTRIES,
    DataInputKey.COMPARISON_DELTAS,
    DataInputKey.RUN_METADATA,
    DataInputKey.ENGINE_CONFIG,
}


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

    # Fetch the run once if any run-dependent key is needed.
    run: SimulationRun | None = None
    if any(k in _RUN_DEPENDENT_KEYS for k in section.data_inputs):
        run = await _fetch_run(run_id, db)

    for key in section.data_inputs:
        if key == DataInputKey.BLUEPRINT:
            pack[key.value] = await _fetch_blueprint(run, db)
        elif key == DataInputKey.TICK_LOGS:
            pack[key.value] = await _fetch_tick_logs(run_id, db)
        elif key == DataInputKey.MC_AGGREGATES:
            # TODO(Day 09): section 14 (Sensitivity Analysis) — when a what-if
            # sweep result is cached for this run, merge it into the pack here
            # so the section writer can reference the sweep grid + breakeven.
            # Optional now: the MC aggregates alone keep the section renderable.
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


def validate_data_pack(pack: dict[str, Any], section: SectionDef) -> list[str]:
    """
    Returns a list of warning strings for any declared input that resolved to None.
    Empty list = pack is complete.
    """
    warnings: list[str] = []
    for key in section.data_inputs:
        value = pack.get(key.value)
        if value is None:
            warnings.append(
                f"DataInputKey.{key.name} resolved to None "
                f"for section {section.section_number}"
            )
    return warnings


# ── Private helpers ──────────────────────────────────────────────────────────


async def _fetch_run(run_id: str, db: AsyncSession) -> SimulationRun | None:
    result = await db.execute(
        select(SimulationRun).where(SimulationRun.id == run_id)
    )
    return result.scalar_one_or_none()


async def _fetch_blueprint(
    run: SimulationRun | None, db: AsyncSession
) -> dict[str, Any] | None:
    if run is None:
        return None
    bpv = await db.get(BlueprintVersion, run.blueprint_version_id)
    return dict(bpv.payload) if bpv else None


async def _fetch_tick_logs(run_id: str, db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        select(TickLog)
        .where(TickLog.run_id == run_id)
        .order_by(TickLog.month)
    )
    ticks = result.scalars().all()
    return [{"month": t.month, **dict(t.kpis)} for t in ticks]


def _extract_mc_aggregates(run: SimulationRun | None) -> dict[str, Any] | None:
    """Return the T27 Monte Carlo aggregation from the run result JSONB."""
    if run is None or run.result is None:
        return None
    result = run.result
    # A completed Monte Carlo run persists `MonteCarloResult`; a baseline/stress
    # run persists a compact one-run outcome. Both are usable upstream.
    return result if ("n_runs" in result or "runs_summary" in result) else None


async def _fetch_vulnerabilities(
    run: SimulationRun | None, db: AsyncSession
) -> list[dict[str, Any]]:
    if run is None:
        return []
    bpv = await db.get(BlueprintVersion, run.blueprint_version_id)
    return list(bpv.vulnerabilities or []) if bpv else []


async def _fetch_optimizations(
    run: SimulationRun | None, db: AsyncSession
) -> list[dict[str, Any]]:
    """Re-run the deterministic counter-factual engine (same seed → same result)."""
    if run is None:
        return []
    bpv = await db.get(BlueprintVersion, run.blueprint_version_id)
    if bpv is None:
        return []
    from app.services.optimization_service import measure_all_tweaks

    tweaks = measure_all_tweaks(dict(bpv.payload), n_runs=20, seed=run.seed or 42)
    return [t.model_dump() for t in tweaks]


def _extract_chronicle(run: SimulationRun | None) -> Any:
    if run is None or run.state_snapshot is None:
        return None
    return run.state_snapshot.get("chronicle")


def _extract_comparison_deltas(run: SimulationRun | None) -> Any:
    if run is None or run.state_snapshot is None:
        return None
    return run.state_snapshot.get("comparison_deltas")


def _extract_run_metadata(run: SimulationRun | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return {
        "run_id": run.id,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "status": run.status,
        "config": run.config,
        "seed": run.config.get("seed") if run.config else None,
    }


def _extract_engine_config(run: SimulationRun | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return run.config


async def _fetch_events_decisions(
    run_id: str, db: AsyncSession
) -> dict[str, list[dict[str, Any]]]:
    events_result = await db.execute(
        select(SimulationEvent)
        .where(SimulationEvent.run_id == run_id)
        .order_by(SimulationEvent.month)
    )
    decisions_result = await db.execute(
        select(Decision)
        .where(Decision.run_id == run_id)
        .order_by(Decision.applied_at)
    )
    events = events_result.scalars().all()
    decisions = decisions_result.scalars().all()
    events_by_id = {e.id: e for e in events}
    return {
        "events": [
            {"month": e.month, "status": e.status, "payload": e.payload}
            for e in events
        ],
        "decisions": [
            {
                "month": events_by_id[d.event_id].month
                if d.event_id in events_by_id
                else None,
                "option_id": d.option_id,
                "projection": d.projection,
            }
            for d in decisions
        ],
    }
