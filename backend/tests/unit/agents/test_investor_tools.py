"""Unit tests for the investor tools agent (Day 22)."""

from __future__ import annotations

from typing import Any

from app.agents.investor_tools import generate_pitch_outline, generate_teaser, teaser_to_pdf
from app.core.config import get_settings
from app.schemas.investor import InvestmentTeaser
from httpx import AsyncClient

MOCK_DATA = {
    "mc_aggregates": {"survival_rate": 0.68, "median_lifespan": 18},
    "tick_logs": [{"month": 1, "revenue": 12000, "cash": 86000}],
    "forge_vulnerabilities": [{"title": "High CAC", "severity": "HIGH"}],
}


def _force_mock() -> None:
    settings = get_settings()
    settings.llm_provider = "mock"
    settings.llm_api_key = ""


async def _workspace(client: AsyncClient, email: str) -> dict[str, Any]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Investor", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login.json()["access_token"]
    ws = await client.post(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Investor Workspace"},
    )
    return {
        "headers": {"Authorization": f"Bearer {token}", "X-Workspace-Id": ws.json()["id"]},
    }


async def test_generate_teaser_returns_teaser() -> None:
    _force_mock()
    result = await generate_teaser(MOCK_DATA)
    assert result.problem
    assert result.simulated_survival
    assert len(result.key_metrics) >= 3


async def test_generate_pitch_outline_has_10_plus_slides() -> None:
    _force_mock()
    result = await generate_pitch_outline(MOCK_DATA)
    assert len(result.slides) >= 10


def test_teaser_to_pdf_returns_bytes() -> None:
    teaser = InvestmentTeaser(
        problem="Test problem.",
        solution="Test solution.",
        simulated_survival="68% survival",
        key_metrics=["MRR: $12k", "CAC: $450", "Runway: 18mo"],
        ask="Raising $500K",
        risks=["High churn"],
    )
    pdf = teaser_to_pdf(teaser, "TestCo", "run_001")
    assert isinstance(pdf, bytes)
    assert len(pdf) > 100


async def test_pitch_slides_have_talking_points() -> None:
    _force_mock()
    result = await generate_pitch_outline(MOCK_DATA)
    assert len(result.slides) >= 10
    assert all(len(slide.talking_points) >= 1 for slide in result.slides)


async def test_teaser_endpoint_returns_pdf(client: AsyncClient) -> None:
    account = await _workspace(client, "investor@b.co")
    resp = await client.post(
        "/api/v1/investor/runs/run_missing/teaser",
        headers=account["headers"],
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 100
