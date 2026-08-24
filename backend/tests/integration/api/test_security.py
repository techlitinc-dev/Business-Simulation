"""T49 security hardening tests: rate limits, CORS, security headers."""

from httpx import AsyncClient


async def test_login_rate_limit_429(client: AsyncClient) -> None:
    """11 rapid login attempts from one IP hit the 10/minute auth limit."""
    from app.core.config import get_settings
    from app.core.rate_limit import reset_windows

    settings = get_settings()
    settings.testing = False  # re-enable the global limiter for this test
    settings.rate_limit_auth = "10/minute"
    reset_windows()
    try:
        for _ in range(10):
            resp = await client.post(
                "/api/v1/auth/login", json={"email": "x@b.co", "password": "password123"}
            )
            # 10 succeed at the auth level (401 for bad creds is still a hit).
            assert resp.status_code == 401
        # 11th → 429.
        resp = await client.post(
            "/api/v1/auth/login", json={"email": "x@b.co", "password": "password123"}
        )
        assert resp.status_code == 429
        assert resp.json() == {"detail": "rate limit exceeded"}
    finally:
        settings.testing = True
        reset_windows()


async def test_register_rate_limit_429(client: AsyncClient) -> None:
    from app.core.config import get_settings
    from app.core.rate_limit import reset_windows

    settings = get_settings()
    settings.testing = False
    settings.rate_limit_register = "20/minute"
    reset_windows()
    try:
        for i in range(20):
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"rl{i}@b.co",
                    "name": "RL",
                    "password": "password123",
                },
            )
            assert resp.status_code == 201, resp.text
        # 21st → 429.
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "rl21@b.co", "name": "RL", "password": "password123"},
        )
        assert resp.status_code == 429
    finally:
        settings.testing = True
        reset_windows()


async def test_global_default_limit_429(client: AsyncClient) -> None:
    from app.core.config import get_settings
    from app.core.rate_limit import reset_windows

    settings = get_settings()
    original_default = settings.rate_limit_default
    settings.testing = False
    settings.rate_limit_default = "5/minute"
    reset_windows()
    try:
        # Non-auth endpoint hits the default limit.
        for _ in range(5):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 429
    finally:
        settings.testing = True
        settings.rate_limit_default = original_default
        reset_windows()


async def test_probes_not_rate_limited(client: AsyncClient) -> None:
    from app.core.config import get_settings
    from app.core.rate_limit import reset_windows

    settings = get_settings()
    original_default = settings.rate_limit_default
    settings.testing = False
    settings.rate_limit_default = "2/minute"
    reset_windows()
    try:
        for _ in range(10):
            resp = await client.get("/health")
            assert resp.status_code == 200
        assert (await client.get("/metrics")).status_code == 200
    finally:
        settings.testing = True
        settings.rate_limit_default = original_default
        reset_windows()


async def test_cors_disallowed_origin_no_header(client: AsyncClient) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    original_origins = settings.cors_origins
    settings.cors_origins = ["http://localhost:5173"]
    try:
        resp = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in resp.headers
    finally:
        settings.cors_origins = original_origins


async def test_cors_allowed_origin_gets_header(client: AsyncClient) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    original_origins = settings.cors_origins
    settings.cors_origins = ["http://localhost:5173"]
    try:
        resp = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    finally:
        settings.cors_origins = original_origins


async def test_security_headers_present(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    # CSP governs framing for every response (same-origin embedding allowed,
    # cross-origin blocked). Non-HTML responses (e.g. the JSON health check,
    # PDF downloads) carry no X-Frame-Options so the same-origin PDF viewer
    # iframe works.
    assert "frame-ancestors 'self'" in resp.headers.get("content-security-policy", "")
    assert "x-frame-options" not in resp.headers
    # HSTS only in production.
    assert "strict-transport-security" not in resp.headers


async def test_html_pages_get_x_frame_options_deny(client: AsyncClient) -> None:
    """Navigable HTML pages are still hard-blocked from framing."""
    resp = await client.get("/docs")
    assert resp.headers.get("content-type", "").startswith("text/html")
    assert resp.headers.get("x-frame-options") == "DENY"


async def test_hsts_only_in_production(client: AsyncClient, monkeypatch) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    settings.environment = "production"
    try:
        resp = await client.get("/health")
        assert resp.headers.get("strict-transport-security") == (
            "max-age=31536000; includeSubDomains"
        )
    finally:
        settings.environment = "development"
