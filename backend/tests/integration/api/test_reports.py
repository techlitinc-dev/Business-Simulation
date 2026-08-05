"""Integration tests for report endpoints (T30/T32/T33)."""

import json
from pathlib import Path

import fakeredis.aioredis
from httpx import AsyncClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> dict:
    return json.loads((FIXTURES / "blueprint_valid.json").read_text())


async def _owner(client: AsyncClient, email: str = "rpt-owner@b.co"):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "RptOwner", "password": "password123"},
    )
    token = (
        await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "password123"}
        )
    ).json()["access_token"]
    resp = await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )
    ws = resp.json()[0]
    return {
        "token": token,
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]},
    }


async def _outsider(client: AsyncClient):
    return await _owner(client, "rpt-outsider@b.co")


async def _make_mc_run(client: AsyncClient, headers: dict, seed: int = 42) -> str:
    resp = await client.post(
        "/api/v1/blueprints",
        json={
            "name": "Rpt BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
        headers=headers,
    )
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=headers)
    version_id = versions.json()[0]["id"]
    start = await client.post(
        "/api/v1/simulations",
        json={
            "blueprint_version_id": version_id,
            "mode": "monte_carlo",
            "seed": seed,
            "config": {"months": 24, "n_runs": 10},
        },
        headers=headers,
    )
    return start.json()["id"]


async def test_report_generates_and_is_idempotent(
    client: AsyncClient, monkeypatch
) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    run_id = await _make_mc_run(client, owner["headers"])

    first = await client.get(
        f"/api/v1/reports/simulations/{run_id}/report", headers=owner["headers"]
    )
    assert first.status_code == 200
    body = first.json()
    assert "### SURVIVAL METRICS" in body["content_md"]
    assert "### ARCHITECTURAL WEAKNESSES" in body["content_md"]
    assert "### AI-GENERATED OPTIMIZATIONS" in body["content_md"]
    assert "### COUNTER-FACTUAL INSIGHT" in body["content_md"]
    survival = body["content_json"]["survival"]
    assert survival["runs_total"] == 10
    assert 0 <= survival["survival_rate"] <= 1
    assert survival["median_lifespan_months"] <= 24
    # Engine-measured impact column present on every optimization row.
    for opt in body["content_json"]["optimizations"]:
        assert opt["impact_on_survival_rate"] is not None
        assert opt["tweak_key"]
        assert opt["recommendation"]
        assert opt["trade_off"]

    second = await client.get(
        f"/api/v1/reports/simulations/{run_id}/report", headers=owner["headers"]
    )
    assert second.status_code == 200
    assert second.json()["id"] == body["id"]
    # Deterministic: two fetches yield identical markdown.
    assert second.json()["content_md"] == body["content_md"]


async def test_report_404_foreign_workspace(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    outsider = await _outsider(client)
    run_id = await _make_mc_run(client, owner["headers"])

    resp = await client.get(
        f"/api/v1/reports/simulations/{run_id}/report", headers=outsider["headers"]
    )
    assert resp.status_code == 404


async def test_report_409_for_pending_run(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    resp = await client.post(
        "/api/v1/blueprints",
        json={
            "name": "Rpt BP2",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
        headers=owner["headers"],
    )
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=owner["headers"])
    version_id = versions.json()[0]["id"]

    # Start a stress run (stops awaiting_decision, not completed).
    run = await client.post(
        "/api/v1/simulations",
        json={"blueprint_version_id": version_id, "mode": "stress", "seed": 3},
        headers=owner["headers"],
    )
    run_id = run.json()["id"]

    report = await client.get(
        f"/api/v1/reports/simulations/{run_id}/report", headers=owner["headers"]
    )
    assert report.status_code == 409


async def test_report_unauthenticated_401(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reports/simulations/run_x/report")
    assert resp.status_code == 401


async def test_export_report_returns_pdf(client: AsyncClient, monkeypatch, tmp_path) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    run_id = await _make_mc_run(client, owner["headers"])

    # Point the endpoint's bound get_settings at a tmp storage dir.
    from app.api.v1.endpoints import reports as reports_module

    settings = reports_module.get_settings()
    settings.report_storage_dir = str(tmp_path)

    resp = await client.post(
        f"/api/v1/reports/simulations/{run_id}/report/export",
        headers=owner["headers"],
    )
    assert resp.status_code == 201
    pdf_url = resp.json()["pdf_url"]
    assert pdf_url.endswith(f"report_{run_id}.pdf")

    file_path = tmp_path / f"report_{run_id}.pdf"
    assert file_path.exists()
    assert file_path.read_bytes().startswith(b"%PDF")


async def test_share_round_trip_public(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    run_id = await _make_mc_run(client, owner["headers"])

    share = await client.post(
        f"/api/v1/reports/simulations/{run_id}/report/share",
        headers=owner["headers"],
    )
    assert share.status_code == 201
    token = share.json()["token"]

    # Public GET — no Authorization header.
    shared = await client.get(f"/api/v1/reports/shared/{token}")
    assert shared.status_code == 200
    body = shared.json()
    assert "### SURVIVAL METRICS" in body["content_md"]
    assert body["run_id"] == run_id


async def test_share_tampered_token_404(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    run_id = await _make_mc_run(client, owner["headers"])
    token = (
        await client.post(
            f"/api/v1/reports/simulations/{run_id}/report/share",
            headers=owner["headers"],
        )
    ).json()["token"]

    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    resp = await client.get(f"/api/v1/reports/shared/{tampered}")
    assert resp.status_code == 404


async def test_share_expired_token_410(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    run_id = await _make_mc_run(client, owner["headers"])

    # Build a token, then monkeypatch the endpoint's serializer loads to
    # simulate max_age being exceeded (SignatureExpired).
    from itsdangerous import SignatureExpired

    share = await client.post(
        f"/api/v1/reports/simulations/{run_id}/report/share",
        headers=owner["headers"],
    )
    token = share.json()["token"]

    def _expired_loads(self, value, max_age):
        raise SignatureExpired("expired")

    from itsdangerous import URLSafeTimedSerializer

    monkeypatch.setattr(URLSafeTimedSerializer, "loads", _expired_loads)

    resp = await client.get(f"/api/v1/reports/shared/{token}")
    assert resp.status_code == 410


# ---------------------------------------------------------------------------
# T33 — comparison endpoint
# ---------------------------------------------------------------------------


async def test_compare_returns_deltas(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    run_a = await _make_mc_run(client, owner["headers"], seed=42)
    run_b = await _make_mc_run(client, owner["headers"], seed=43)

    resp = await client.get(
        f"/api/v1/reports/compare?a={run_a}&b={run_b}", headers=owner["headers"]
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"a", "b", "deltas", "kill_vector_changes", "verdict"}
    assert body["deltas"]["survival_rate_pp"] == round(
        (body["b"]["survival_rate"] - body["a"]["survival_rate"]) * 100, 1
    )
    assert body["verdict"] in ("improved", "regressed", "unchanged")
    # Kill vector changes sorted by |delta_pp| desc.
    deltas = [abs(c["delta_pp"]) for c in body["kill_vector_changes"]]
    assert deltas == sorted(deltas, reverse=True)


async def test_compare_self_unchanged(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    run_a = await _make_mc_run(client, owner["headers"], seed=42)

    resp = await client.get(
        f"/api/v1/reports/compare?a={run_a}&b={run_a}", headers=owner["headers"]
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "unchanged"
    assert body["deltas"]["survival_rate_pp"] == 0
    assert body["deltas"]["median_lifespan_months"] == 0


async def test_compare_404_foreign_workspace(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    outsider = await _outsider(client)
    run_a = await _make_mc_run(client, owner["headers"])
    run_b = await _make_mc_run(client, outsider["headers"])

    resp = await client.get(
        f"/api/v1/reports/compare?a={run_a}&b={run_b}", headers=outsider["headers"]
    )
    assert resp.status_code == 404


async def test_compare_409_for_pending_run(client: AsyncClient, monkeypatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.api.deps.get_redis", lambda: fake)

    owner = await _owner(client)
    run_a = await _make_mc_run(client, owner["headers"])

    # A stress run stuck awaiting_decision is not completed.
    resp = await client.post(
        "/api/v1/blueprints",
        json={
            "name": "Cmp BP",
            "industry": "B2B SaaS",
            "stage": "Seed",
            "payload": _valid_payload(),
        },
        headers=owner["headers"],
    )
    bp_id = resp.json()["id"]
    versions = await client.get(f"/api/v1/blueprints/{bp_id}/versions", headers=owner["headers"])
    stress = await client.post(
        "/api/v1/simulations",
        json={
            "blueprint_version_id": versions.json()[0]["id"],
            "mode": "stress",
            "seed": 9,
        },
        headers=owner["headers"],
    )
    run_b = stress.json()["id"]

    resp = await client.get(
        f"/api/v1/reports/compare?a={run_a}&b={run_b}", headers=owner["headers"]
    )
    assert resp.status_code == 409
