"""Unit tests for DomainError and the catch-all exception handler."""

import pytest
from app.core.exceptions import DomainError, register_exception_handlers
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/domain")
    async def domain_route() -> None:
        raise DomainError(status_code=422, detail="x")

    @app.get("/boom")
    async def boom_route() -> None:
        raise RuntimeError("secret internals")

    return app


@pytest.fixture
def client() -> TestClient:
    # raise_server_exceptions=False lets the 500 handler run instead of
    # propagating the exception into the test (Starlette always re-raises
    # after the ServerErrorMiddleware handler executes).
    with TestClient(_make_app(), raise_server_exceptions=False) as c:
        yield c


def test_domain_error_maps_to_status_and_detail(client: TestClient) -> None:
    resp = client.get("/domain")
    assert resp.status_code == 422
    assert resp.json() == {"detail": "x"}


def test_unhandled_exception_returns_500_without_leaking_traceback(
    client: TestClient,
) -> None:
    resp = client.get("/boom")
    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal server error"}
    assert "secret internals" not in resp.text
