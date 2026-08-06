"""T49 audit log tests: middleware writes + admin retrieval."""


from httpx import AsyncClient


async def test_mutating_request_writes_audit_row(client: AsyncClient) -> None:
    """A POST (register) produces exactly one audit_log row."""
    from app.core.config import get_settings
    from app.db.session import async_session_factory
    from app.models.audit_log import AuditLog
    from sqlalchemy import select

    settings = get_settings()
    settings.testing = False  # enable the audit middleware for this test
    try:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "audit1@b.co", "name": "Audit", "password": "password123"},
        )
        assert resp.status_code == 201
        request_id = resp.headers.get("X-Request-ID")
        assert request_id

        async with async_session_factory() as session:
            rows = (await session.scalars(select(AuditLog))).all()
            assert len(rows) == 1
            row = rows[0]
            assert row.method == "POST"
            assert row.path == "/api/v1/auth/register"
            assert row.status_code == 201
            assert row.request_id == request_id
            # Register carries no JWT → user_id is null (attribution happens
            # for authenticated mutating requests, tested below).
            assert row.user_id is None
    finally:
        settings.testing = True


async def test_blueprint_post_writes_audit_with_user_id(client: AsyncClient) -> None:
    import json
    from pathlib import Path

    from app.db.session import async_session_factory
    from app.models.audit_log import AuditLog
    from app.models.user import User
    from sqlalchemy import select

    FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
    payload = json.loads((FIXTURES / "blueprint_valid.json").read_text())

    from app.core.config import get_settings

    settings = get_settings()
    settings.testing = False
    try:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "audit2@b.co", "name": "A2", "password": "password123"},
        )
        login = await client.post(
            "/api/v1/auth/login", json={"email": "audit2@b.co", "password": "password123"}
        )
        token = login.json()["access_token"]
        ws = (await client.get(
            "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
        )).json()[0]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws["id"]}

        resp = await client.post(
            "/api/v1/blueprints",
            headers=headers,
            json={
                "name": "Audit BP",
                "industry": "B2B SaaS",
                "stage": "Seed",
                "payload": payload,
            },
        )
        assert resp.status_code == 201
        request_id = resp.headers.get("X-Request-ID")

        async with async_session_factory() as session:
            # Find the audit row for the blueprint POST.
            rows = (
                await session.scalars(
                    select(AuditLog).where(AuditLog.path == "/api/v1/blueprints")
                )
            ).all()
            assert len(rows) == 1
            row = rows[0]
            assert row.method == "POST"
            assert row.status_code == 201
            assert row.request_id == request_id

            user = await session.scalar(select(User).where(User.email == "audit2@b.co"))
            assert row.user_id == user.id
    finally:
        settings.testing = True


async def test_failed_audit_write_does_not_break_response(
    client: AsyncClient, monkeypatch
) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    settings.testing = False

    async def _boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr("app.core.audit._write_audit_row", _boom)
    try:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "audit3@b.co", "name": "A3", "password": "password123"},
        )
        assert resp.status_code == 201  # response unaffected by audit failure
    finally:
        settings.testing = True


async def _admin_headers(client: AsyncClient, email: str) -> dict:
    from app.db.session import async_session_factory
    from app.models.user import User
    from sqlalchemy import select

    await client.post(
        "/api/v1/auth/register", json={"email": email, "name": "Adm", "password": "password123"}
    )
    async with async_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == email))
        user.is_admin = True
        await session.commit()
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_admin_audit_log_returns_rows(client: AsyncClient) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    settings.testing = False
    try:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "audit4@b.co", "name": "A4", "password": "password123"},
        )
        admin_headers = await _admin_headers(client, "audit4admin@b.co")

        resp = await client.get("/api/v1/admin/audit-log", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        # At least the register from this test + the admin's own register.
        assert body["total"] >= 2
        assert any(item["path"] == "/api/v1/auth/register" for item in body["items"])
    finally:
        settings.testing = True


async def test_admin_audit_log_forbidden_for_non_admin(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "audit5@b.co", "name": "A5", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "audit5@b.co", "password": "password123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = await client.get("/api/v1/admin/audit-log", headers=headers)
    assert resp.status_code == 403


async def test_admin_audit_log_filters_by_path(client: AsyncClient) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    settings.testing = False
    try:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "audit6@b.co", "name": "A6", "password": "password123"},
        )
        admin_headers = await _admin_headers(client, "audit6admin@b.co")

        resp = await client.get(
            "/api/v1/admin/audit-log?path=register", headers=admin_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert all("register" in item["path"] for item in body["items"])
    finally:
        settings.testing = True
