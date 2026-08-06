"""Additional coverage for API edge branches (T47).

Drives the remaining uncovered paths across reports, simulations,
scenarios, api_keys, and the workspace/deps guards.
"""

import json
from pathlib import Path

import fakeredis.aioredis
from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _register(client: AsyncClient, email: str) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Cov", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = (await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )).json()[0]
    return {
        "token": token,
        "workspace_id": ws["id"],
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]},
    }


async def _create_blueprint_version(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/blueprints",
        headers=headers,
        json={
            "name": "Cov BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
    )
    assert resp.status_code == 201, resp.text
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=headers)
    return versions.json()[0]["id"]


async def _make_mc_run(client: AsyncClient, headers: dict, n_runs: int = 5) -> str:
    bpv = await _create_blueprint_version(client, headers)
    start = await client.post(
        "/api/v1/simulations",
        headers=headers,
        json={
            "blueprint_version_id": bpv,
            "mode": "monte_carlo",
            "seed": 42,
            "config": {"months": 24, "n_runs": n_runs},
        },
    )
    assert start.status_code == 201, start.text
    return start.json()["id"]


# ---------------------------------------------------------------------------
# Reports — DomainError branches
# ---------------------------------------------------------------------------


async def test_report_export_on_baseline_run_409(client: AsyncClient) -> None:
    """A baseline run cannot export a report (only mc/stress)."""
    account = await _register(client, "cov1@b.co")
    bpv = await _create_blueprint_version(client, account["headers"])
    run = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={"blueprint_version_id": bpv, "mode": "baseline", "seed": 1},
    )
    run_id = run.json()["id"]

    resp = await client.post(
        f"/api/v1/reports/simulations/{run_id}/report/export",
        headers=account["headers"],
    )
    assert resp.status_code == 409


async def test_report_share_on_baseline_run_409(client: AsyncClient) -> None:
    account = await _register(client, "cov2@b.co")
    bpv = await _create_blueprint_version(client, account["headers"])
    run = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={"blueprint_version_id": bpv, "mode": "baseline", "seed": 1},
    )
    run_id = run.json()["id"]

    resp = await client.post(
        f"/api/v1/reports/simulations/{run_id}/report/share",
        headers=account["headers"],
    )
    assert resp.status_code == 409


async def test_report_export_pdf_failure_500(client: AsyncClient, monkeypatch, tmp_path) -> None:
    from app.api.v1.endpoints import reports as reports_module

    settings = reports_module.get_settings()
    settings.report_storage_dir = str(tmp_path)

    # Force the PDF renderer to fail.
    def _boom(*args, **kwargs):
        raise RuntimeError("weasyprint exploded")

    monkeypatch.setattr("app.utils.pdf.render_report_pdf", _boom)

    account = await _register(client, "cov3@b.co")
    run_id = await _make_mc_run(client, account["headers"])

    resp = await client.post(
        f"/api/v1/reports/simulations/{run_id}/report/export",
        headers=account["headers"],
    )
    assert resp.status_code == 500


async def test_shared_report_missing_run_404(client: AsyncClient) -> None:
    """A share token pointing at a deleted run returns 404."""
    from app.db.session import async_session_factory

    account = await _register(client, "cov4@b.co")
    run_id = await _make_mc_run(client, account["headers"])

    # Generate + share.
    await client.get(f"/api/v1/reports/simulations/{run_id}/report", headers=account["headers"])
    share = await client.post(
        f"/api/v1/reports/simulations/{run_id}/report/share",
        headers=account["headers"],
    )
    token = share.json()["token"]

    # Delete the run so the shared lookup finds report but no run.
    from app.models.simulation import SimulationRun

    async with async_session_factory() as session:
        run = await session.get(SimulationRun, run_id)
        await session.delete(run)
        await session.commit()

    resp = await client.get(f"/api/v1/reports/shared/{token}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Simulations — remaining branches
# ---------------------------------------------------------------------------


async def test_mc_run_plan_limit_402(client: AsyncClient, monkeypatch) -> None:
    """Monte Carlo batch exceeding the tier limit → 402."""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    account = await _register(client, "cov5@b.co")
    bpv = await _create_blueprint_version(client, account["headers"])

    # free tier allows 25 mc ticks/batch; request 26.
    resp = await client.post(
        "/api/v1/simulations",
        headers=account["headers"],
        json={
            "blueprint_version_id": bpv,
            "mode": "monte_carlo",
            "seed": 1,
            "config": {"n_runs": 26},
        },
    )
    assert resp.status_code == 402


async def test_mc_run_increments_ticks(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    account = await _register(client, "cov6@b.co")
    run_id = await _make_mc_run(client, account["headers"], n_runs=4)

    usage = (await client.get(
        "/api/v1/billing/usage", headers=account["headers"]
    )).json()
    assert usage["usage"]["mc_ticks_used"] == 4
    assert run_id


async def test_patch_run_not_found_404(client: AsyncClient) -> None:
    account = await _register(client, "cov7@b.co")
    resp = await client.patch(
        "/api/v1/simulations/run_missing",
        headers=account["headers"],
        json={"is_public": True},
    )
    assert resp.status_code == 404


async def test_patch_run_foreign_403(client: AsyncClient, monkeypatch) -> None:
    from app.db.session import async_session_factory
    from app.models.simulation import SimulationRun

    owner = await _register(client, "cov8@b.co")
    run_id = await _make_mc_run(client, owner["headers"])

    # Rewrite the run's workspace to another user's ws.
    outsider = await _register(client, "cov8b@b.co")
    import uuid as _uuid

    async with async_session_factory() as session:
        run = await session.get(SimulationRun, run_id)
        run.workspace_id = _uuid.UUID(outsider["workspace_id"])
        await session.commit()

    # The owner no longer matches the run's workspace → 403.
    resp = await client.patch(
        f"/api/v1/simulations/{run_id}",
        headers=owner["headers"],
        json={"is_public": True},
    )
    assert resp.status_code == 403


async def test_ticks_unknown_run_404(client: AsyncClient) -> None:
    account = await _register(client, "cov9@b.co")
    resp = await client.get(
        "/api/v1/simulations/run_missing/ticks", headers=account["headers"]
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scenarios — DomainError branches
# ---------------------------------------------------------------------------


async def test_scenario_get_unknown_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/scenarios/scn_unknown")
    assert resp.status_code == 404


async def test_scenario_get_private_with_auth_404(client: AsyncClient) -> None:
    author = await _register(client, "cov10@b.co")
    bpv = await _create_blueprint_version(client, author["headers"])
    created = await client.post(
        "/api/v1/scenarios",
        headers=author["headers"],
        json={
            "title": "Private Cov",
            "description": "D",
            "category": "custom",
            "blueprint_version_id": bpv,
        },
    )
    scenario_id = created.json()["id"]

    from app.db.session import async_session_factory
    from app.models.scenario import Scenario

    async with async_session_factory() as session:
        scenario = await session.get(Scenario, scenario_id)
        scenario.is_public = False
        await session.commit()

    # Outsider (with auth) still gets 404.
    outsider = await _register(client, "cov10b@b.co")
    resp = await client.get(
        f"/api/v1/scenarios/{scenario_id}", headers=outsider["headers"]
    )
    assert resp.status_code == 404


async def test_scenario_publish_unknown_version_404(client: AsyncClient) -> None:
    account = await _register(client, "cov11@b.co")
    resp = await client.post(
        "/api/v1/scenarios",
        headers=account["headers"],
        json={
            "title": "X",
            "description": "D",
            "category": "custom",
            "blueprint_version_id": "bpv_unknown",
        },
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API keys — member denied
# ---------------------------------------------------------------------------


async def test_api_key_list_requires_admin(client: AsyncClient) -> None:
    import uuid

    from app.core.security import create_access_token
    from app.db.session import async_session_factory
    from app.models.user import User
    from app.models.workspace import Membership, Role, Workspace

    owner = await _register(client, "cov12@b.co")

    async with async_session_factory() as session:
        ws = await session.get(Workspace, uuid.UUID(owner["workspace_id"]))
        member = User(email="cov12m@b.co", name="Member", pw_hash="x")
        session.add(member)
        await session.flush()
        session.add(Membership(user_id=member.id, workspace_id=ws.id, role=Role.MEMBER))
        await session.commit()

    member_token = create_access_token(str(member.id))
    member_headers = {
        "Authorization": f"Bearer {member_token}",
        "X-Workspace-Id": owner["workspace_id"],
    }

    resp = await client.get("/api/v1/api-keys", headers=member_headers)
    assert resp.status_code == 403
