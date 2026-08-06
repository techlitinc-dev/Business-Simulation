"""T48 observability integration tests: request-id, /metrics, /ready probes."""

from httpx import AsyncClient


async def test_health_returns_ok_with_request_id(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": "0.1.0"}
    # Every response carries an X-Request-ID.
    assert resp.headers.get("X-Request-ID")


async def test_request_id_preserved_verbatim(client: AsyncClient) -> None:
    resp = await client.get("/health", headers={"X-Request-ID": "my-trace-id-123"})
    assert resp.headers.get("X-Request-ID") == "my-trace-id-123"


async def test_request_id_generated_when_absent(client: AsyncClient) -> None:
    r1 = await client.get("/health")
    r2 = await client.get("/health")
    assert r1.headers["X-Request-ID"]
    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


async def test_metrics_exposes_http_requests_total(client: AsyncClient) -> None:
    # Hit an endpoint so a counter exists.
    await client.get("/health")
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text
    content_type = resp.headers.get("content-type", "")
    assert "openmetrics" in content_type or "text/plain" in content_type


async def test_ready_returns_200_when_checks_pass(
    client: AsyncClient, monkeypatch
) -> None:
    import fakeredis.aioredis

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

    # Point the ready probe's Redis client at fakeredis.
    monkeypatch.setattr(
        "redis.asyncio.Redis.from_url", lambda *a, **kw: fake
    )

    resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"] == {"db": "ok", "redis": "ok"}


async def test_ready_returns_503_when_db_check_fails(
    client: AsyncClient, monkeypatch
) -> None:
    import fakeredis.aioredis

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("redis.asyncio.Redis.from_url", lambda *a, **kw: fake)

    # Break the DB check by making execute raise.
    async def _boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr("app.db.session.async_session_factory", _boom)

    resp = await client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not ready"
    assert body["checks"]["db"] == "error"


async def test_ready_returns_503_when_redis_check_fails(
    client: AsyncClient, monkeypatch
) -> None:
    # Fake Redis that raises on ping.
    class _BoomRedis:
        async def ping(self) -> bool:
            raise RuntimeError("redis down")

        async def aclose(self) -> None:
            pass

    monkeypatch.setattr("redis.asyncio.Redis.from_url", lambda *a, **kw: _BoomRedis())

    resp = await client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not ready"
    assert body["checks"]["db"] == "ok"
    assert body["checks"]["redis"] == "error"
