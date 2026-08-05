"""Unit tests for the resilience audit report service (T30/T33)."""

import json
from pathlib import Path

import pytest
from app.db.session import async_session_factory
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.report import Report
from app.models.simulation import SimulationRun
from app.models.workspace import Workspace
from app.schemas.report import ReportContent
from app.services import report_service
from app.services.report_service import (
    build_report_content,
    survival_metrics_from_result,
)
from sqlalchemy import select

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _blueprint_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_golden.json").read_text())


def _mc_result() -> dict:
    # 34 survivors (24 months) + 66 failures at 11 months → median lands on 11.
    lifespans = [24] * 34 + [11] * 66
    return {
        "n_runs": 100,
        "survival_rate": 0.34,
        "median_lifespan_months": 11,
        "p25_lifespan_months": 7,
        "p75_lifespan_months": 18,
        "kill_vectors": {"financial": 30, "market": 22, "natural_causes": 14},
        "runs_summary": [
            {
                "seed": i,
                "survived": i < 34,
                "lifespan_months": lifespans[i],
            }
            for i in range(100)
        ],
    }


def test_survival_metrics_math() -> None:
    metrics = survival_metrics_from_result(_mc_result())
    assert metrics.runs_total == 100
    assert metrics.runs_survived == 34
    assert metrics.survival_rate == pytest.approx(0.34)
    assert metrics.median_lifespan_months == 11
    assert [kv.cause for kv in metrics.kill_vectors] == [
        "financial", "market", "natural_causes"
    ]
    total_pct = sum(kv.pct for kv in metrics.kill_vectors)
    assert total_pct == pytest.approx(100.0, abs=0.2)


def test_kill_vectors_sorted_by_count_desc() -> None:
    metrics = survival_metrics_from_result(_mc_result())
    counts = [kv.count for kv in metrics.kill_vectors]
    assert counts == sorted(counts, reverse=True)


def test_render_survival_markdown_has_required_headings() -> None:
    metrics = survival_metrics_from_result(_mc_result())
    md = report_service.render_survival_markdown(metrics)
    assert "### SURVIVAL METRICS" in md
    assert "34%" in md
    assert "11 months" in md


def test_weaknesses_ranked_by_severity() -> None:
    metrics = survival_metrics_from_result(_mc_result())
    vulnerabilities = [
        {"severity": "high", "description": "Tight runway", "mitigation_suggestion": "Cut burn"},
        {"severity": "low", "description": "Weak brand", "mitigation_suggestion": "Invest"},
    ]
    content = build_report_content(metrics, vulnerabilities)
    assert content.weaknesses[0].severity == "CRITICAL"  # 43% kill vector
    assert "HIGH" in [w.severity for w in content.weaknesses]
    assert "LOW" in [w.severity for w in content.weaknesses]


def test_render_full_markdown_contains_headings() -> None:
    metrics = survival_metrics_from_result(_mc_result())
    content = build_report_content(metrics, [])
    md = report_service.render_full_markdown(content)
    assert "### SURVIVAL METRICS" in md
    assert "### ARCHITECTURAL WEAKNESSES" in md


def test_byte_identical_for_same_input() -> None:
    metrics_a = survival_metrics_from_result(_mc_result())
    metrics_b = survival_metrics_from_result(_mc_result())
    md_a = report_service.render_survival_markdown(metrics_a)
    md_b = report_service.render_survival_markdown(metrics_b)
    assert md_a == md_b


async def test_generate_is_idempotent() -> None:
    async with async_session_factory() as session:
        ws = Workspace(name="Rpt WS", slug="rpt-ws")
        session.add(ws)
        await session.flush()
        bp = Blueprint(workspace_id=ws.id, name="B", industry="SaaS", stage="Seed")
        session.add(bp)
        await session.flush()
        version = BlueprintVersion(
            blueprint_id=bp.id, version=1, payload=_blueprint_payload()
        )
        session.add(version)
        await session.flush()
        run = SimulationRun(
            workspace_id=ws.id, blueprint_version_id=version.id, mode="monte_carlo",
            status="completed", seed=1, current_month=24,
            config={"months": 24, "n_runs": 100},
            result=_mc_result(),
        )
        session.add(run)
        await session.commit()
        run_id = run.id

        first = await report_service.generate_resilience_audit(
            session, workspace_id=ws.id, run_id=run_id
        )
        second = await report_service.generate_resilience_audit(
            session, workspace_id=ws.id, run_id=run_id
        )
        assert first.id == second.id

        rows = (await session.scalars(select(Report))).all()
        assert len(rows) == 1
        content = ReportContent.model_validate(first.content_json)
        assert content.survival.survival_rate == pytest.approx(0.34)
        assert content.survival.median_lifespan_months == 11


async def test_generate_409_for_non_completed() -> None:
    async with async_session_factory() as session:
        ws = Workspace(name="Rpt WS2", slug="rpt-ws2")
        session.add(ws)
        await session.flush()
        run = SimulationRun(
            workspace_id=ws.id, blueprint_version_id="bpv_x", mode="monte_carlo",
            status="pending", seed=1, current_month=0,
            config={"months": 24, "n_runs": 10}, result=None,
        )
        session.add(run)
        await session.commit()
        with pytest.raises(Exception) as excinfo:
            await report_service.generate_resilience_audit(
                session, workspace_id=ws.id, run_id=run.id
            )
        assert getattr(excinfo.value, "status_code", None) == 409


# ---------------------------------------------------------------------------
# T33 — comparison
# ---------------------------------------------------------------------------


def _result(survived: int, n_runs: int = 100) -> dict:
    return {
        "n_runs": n_runs,
        "survival_rate": round(survived / n_runs, 4),
        "median_lifespan_months": 11,
        "p25_lifespan_months": 7,
        "p75_lifespan_months": 18,
        "kill_vectors": {"financial": n_runs - survived},
        "runs_summary": [
            {"seed": i, "survived": i < survived, "lifespan_months": 24 if i < survived else 9}
            for i in range(n_runs)
        ],
    }


async def _seed_two_runs(result_a: dict, result_b: dict) -> tuple[str, str]:
    async with async_session_factory() as session:
        ws = Workspace(name="Cmp WS", slug="cmp-ws")
        session.add(ws)
        await session.flush()
        bp = Blueprint(workspace_id=ws.id, name="B", industry="SaaS", stage="Seed")
        session.add(bp)
        await session.flush()
        v1 = BlueprintVersion(blueprint_id=bp.id, version=1, payload=_blueprint_payload())
        v2 = BlueprintVersion(blueprint_id=bp.id, version=2, payload=_blueprint_payload())
        session.add_all([v1, v2])
        await session.flush()
        run_a = SimulationRun(
            workspace_id=ws.id, blueprint_version_id=v1.id, mode="monte_carlo",
            status="completed", seed=1, current_month=24,
            config={"months": 24, "n_runs": 100}, result=result_a,
        )
        run_b = SimulationRun(
            workspace_id=ws.id, blueprint_version_id=v2.id, mode="monte_carlo",
            status="completed", seed=2, current_month=24,
            config={"months": 24, "n_runs": 100}, result=result_b,
        )
        session.add_all([run_a, run_b])
        await session.commit()
        return run_a.id, run_b.id


async def test_compare_delta_math_and_verdict() -> None:
    run_a_id, run_b_id = await _seed_two_runs(_result(34), _result(52))
    async with async_session_factory() as session:
        result = await report_service.compare_runs(
            session, workspace_id=(await _ws_id(session)), run_a_id=run_a_id, run_b_id=run_b_id
        )
    assert result.deltas.survival_rate_pp == pytest.approx(18.0)
    assert result.verdict == "improved"
    assert result.a.survival_rate == pytest.approx(0.34)
    assert result.b.survival_rate == pytest.approx(0.52)
    assert result.a.blueprint_version == 1
    assert result.b.blueprint_version == 2


async def test_compare_self_unchanged() -> None:
    run_a_id, run_b_id = await _seed_two_runs(_result(34), _result(34))
    async with async_session_factory() as session:
        result = await report_service.compare_runs(
            session, workspace_id=(await _ws_id(session)), run_a_id=run_a_id, run_b_id=run_b_id
        )
    assert result.verdict == "unchanged"
    assert result.deltas.survival_rate_pp == 0.0
    assert result.deltas.median_lifespan_months == 0


async def test_compare_regressed() -> None:
    run_a_id, run_b_id = await _seed_two_runs(_result(52), _result(30))
    async with async_session_factory() as session:
        result = await report_service.compare_runs(
            session, workspace_id=(await _ws_id(session)), run_a_id=run_a_id, run_b_id=run_b_id
        )
    assert result.verdict == "regressed"
    assert result.deltas.survival_rate_pp == pytest.approx(-22.0)


async def test_compare_kill_vector_changes_sorted() -> None:
    run_a_id, run_b_id = await _seed_two_runs(_result(34), _result(52))
    async with async_session_factory() as session:
        result = await report_service.compare_runs(
            session, workspace_id=(await _ws_id(session)), run_a_id=run_a_id, run_b_id=run_b_id
        )
    deltas = [abs(c.delta_pp) for c in result.kill_vector_changes]
    assert deltas == sorted(deltas, reverse=True)
    # Kill vector % fell from 100% of failures to ~100% of fewer failures.
    assert result.kill_vector_changes[0].cause == "financial"


async def _ws_id(session) -> object:
    from app.models.workspace import Workspace as WS

    return (await session.scalars(select(WS))).first().id
