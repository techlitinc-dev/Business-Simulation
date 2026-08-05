"""Structural validation rule tests for blueprints (T16)."""

import copy
import json
from pathlib import Path

from app.schemas.blueprint import BlueprintPayload
from app.services.blueprint_service import validate_blueprint

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _payload(**mutations) -> BlueprintPayload:
    """Build a valid payload from the fixture, applying nested-key mutations.

    Bare field names (``ltv``, ``cac``, ...) target the first revenue stream;
    dotted paths (``cost_structure.fixed_monthly``, ``financials.starting_capital``)
    target any nested key.
    """
    raw = json.loads((FIXTURES / "blueprint_valid.json").read_text())

    def apply(obj, dotted: str, value) -> None:
        *parts, leaf = dotted.split(".")
        cur: dict | list = raw["revenue_engine"]["streams"][0] if not parts else raw
        for part in parts:
            if isinstance(cur, list):
                cur = cur[int(part)]
            else:
                key = int(part) if part.isdigit() else part
                cur = cur[key]
        cur[leaf] = value

    for dotted, value in mutations.items():
        apply(raw, dotted, value)
    return BlueprintPayload.model_validate(raw)


def _codes(report) -> set[str]:
    return {i.code for i in [*report.errors, *report.warnings]}


def test_fixture_payload_is_valid() -> None:
    report = validate_blueprint(_payload())
    assert report.is_valid is True
    assert report.errors == []
    # Fixture: LTV:CAC 2.8 < 3, runway 11.1 < 18, single stream = 100% concentration
    assert {w.code for w in report.warnings} == {
        "LTV_CAC_RATIO",
        "INSUFFICIENT_RUNWAY",
        "REVENUE_CONCENTRATION",
    }


def test_ltv_cac_warning_and_message() -> None:
    report = validate_blueprint(_payload(ltv=1000, cac=850))
    warning = next(w for w in report.warnings if w.code == "LTV_CAC_RATIO")
    assert "3:1 survival threshold" in warning.message
    assert "1.2:1" in warning.message
    assert report.is_valid is True


def test_healthy_ltv_cac_no_warning() -> None:
    report = validate_blueprint(_payload(ltv=3000, cac=850))
    assert "LTV_CAC_RATIO" not in _codes(report)


def test_negative_unit_economics_is_error() -> None:
    report = validate_blueprint(_payload(ltv=500, cac=850))
    assert report.is_valid is False
    assert any(i.code == "NEGATIVE_UNIT_ECONOMICS" for i in report.errors)


def test_negative_contribution_margin_is_error() -> None:
    report = validate_blueprint(
        _payload(price_point=10, **{"cost_structure.variable_per_unit": 12})
    )
    assert report.is_valid is False
    assert any(i.code == "NEGATIVE_CONTRIBUTION_MARGIN" for i in report.errors)


def test_insufficient_runway_warning() -> None:
    report = validate_blueprint(
        _payload(
            **{
                "financials.starting_capital": 100000,
                "cost_structure.burn_rate_month_1": 45000,
                "financials.target_runway_months": 18,
            },
        )
    )
    warning = next(w for w in report.warnings if w.code == "INSUFFICIENT_RUNWAY")
    assert "2.2 months" in warning.message
    assert report.is_valid is True


def test_zero_burn_skips_runway_check() -> None:
    report = validate_blueprint(_payload(**{"cost_structure.burn_rate_month_1": 0}))
    assert "INSUFFICIENT_RUNWAY" not in _codes(report)


def test_revenue_concentration_warning() -> None:
    # Mutate the fixture into two streams, one holding 80% of projected M12 revenue.
    payload = _payload()
    stream_a = payload.revenue_engine.streams[0].model_dump()
    stream_b = copy.deepcopy(stream_a)
    stream_b["name"] = "Secondary"
    # A: 99 * 500 = 49,500 (80%)  B: 99 * 125 = 12,375 (20%) -> total 61,875
    stream_a["projected_customers_month_12"] = 500
    stream_b["projected_customers_month_12"] = 125
    payload.revenue_engine.streams = [
        type(payload.revenue_engine.streams[0])(**stream_a),
        type(payload.revenue_engine.streams[0])(**stream_b),
    ]

    report = validate_blueprint(payload)
    assert any(w.code == "REVENUE_CONCENTRATION" for w in report.warnings)


def test_empty_streams_is_error() -> None:
    payload = _payload()
    payload.revenue_engine.streams = []
    report = validate_blueprint(payload)
    assert report.is_valid is False
    assert any(i.code == "NO_REVENUE_STREAMS" for i in report.errors)


def test_warnings_never_block() -> None:
    report = validate_blueprint(_payload(ltv=1000, cac=850))
    assert report.is_valid is True
    assert report.errors == []


def test_report_field_shape() -> None:
    report = validate_blueprint(_payload(ltv=500, cac=850))
    error = next(i for i in report.errors if i.code == "NEGATIVE_UNIT_ECONOMICS")
    assert error.severity == "error"
    assert "streams" in error.field
    assert error.message
