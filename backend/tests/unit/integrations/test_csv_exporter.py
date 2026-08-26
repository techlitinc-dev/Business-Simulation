"""Unit tests for integrations — CSV export + webhook signing."""

from __future__ import annotations

from app.services.integrations.csv_exporter import mc_to_csv, ticks_to_csv
from app.services.integrations.webhook_service import _sign_payload

TICKS = [
    {"month": 1, "revenue": 12000, "cash": 86000},
    {"month": 2, "revenue": 15000, "cash": 87000},
]

MC = {
    "survival_rate": 0.68,
    "median_lifespan": 18,
    # Real MonteCarloResult shape: kill_vectors is a dict[type -> count].
    "kill_vectors": {"cash_out": 12, "churn_death": 8},
}


def test_ticks_to_csv_has_header() -> None:
    csv_content = ticks_to_csv(TICKS)
    assert "month" in csv_content
    assert "revenue" in csv_content
    assert "12000" in csv_content


def test_ticks_to_csv_row_count() -> None:
    csv_content = ticks_to_csv(TICKS)
    lines = [line for line in csv_content.strip().split("\n") if line]
    assert len(lines) == 3  # header + 2 rows


def test_mc_to_csv_has_survival_rate() -> None:
    csv_content = mc_to_csv(MC)
    assert "survival_rate" in csv_content
    assert "0.68" in csv_content


def test_mc_to_csv_includes_kill_vectors() -> None:
    csv_content = mc_to_csv(MC)
    assert "cash_out" in csv_content
    assert "12" in csv_content


def test_sign_payload_deterministic() -> None:
    sig1 = _sign_payload({"event": "run.completed", "run_id": "x"}, "secret123")
    sig2 = _sign_payload({"event": "run.completed", "run_id": "x"}, "secret123")
    assert sig1 == sig2


def test_sign_payload_different_secret() -> None:
    sig1 = _sign_payload({"event": "test"}, "secret1")
    sig2 = _sign_payload({"event": "test"}, "secret2")
    assert sig1 != sig2
