"""Schema tests for the Format A blueprint contract (T16)."""

import json
from pathlib import Path

import pytest
from app.schemas.blueprint import BlueprintPayload
from pydantic import ValidationError

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _valid_payload() -> BlueprintPayload:
    raw = json.loads((FIXTURES / "blueprint_valid.json").read_text())
    return BlueprintPayload.model_validate(raw)


def test_fixture_round_trips_field_for_field() -> None:
    raw = json.loads((FIXTURES / "blueprint_valid.json").read_text())
    payload = BlueprintPayload.model_validate(raw)

    dumped = payload.model_dump(mode="json")
    assert dumped == raw


def test_defaults_applied() -> None:
    raw = json.loads((FIXTURES / "blueprint_valid.json").read_text())
    payload = BlueprintPayload.model_validate(raw)
    assert payload.simulation_parameters.time_step == "monthly"
    assert payload.simulation_parameters.monte_carlo_runs == 100
    assert payload.simulation_parameters.random_seed is None


@pytest.mark.parametrize(
    "mutator",
    [
        # Top-level unknown key
        lambda raw: raw.update({"mystery_field": 1}),
        # Unknown key in a nested model
        lambda raw: raw["business_profile"].update({"unknown": "x"}),
        # Unknown key in a stream
        lambda raw: raw["revenue_engine"]["streams"][0].update({"sizzle": True}),
        # Unknown key in simulation parameters
        lambda raw: raw["simulation_parameters"].update({"nope": 1}),
    ],
)
def test_extra_fields_rejected(mutator) -> None:
    raw = json.loads((FIXTURES / "blueprint_valid.json").read_text())
    mutator(raw)
    with pytest.raises(ValidationError):
        BlueprintPayload.model_validate(raw)


def test_missing_required_field_rejected() -> None:
    raw = json.loads((FIXTURES / "blueprint_valid.json").read_text())
    del raw["financials"]
    with pytest.raises(ValidationError):
        BlueprintPayload.model_validate(raw)


def test_constraint_violations_rejected() -> None:
    raw = json.loads((FIXTURES / "blueprint_valid.json").read_text())
    stream = raw["revenue_engine"]["streams"][0]
    stream["price_point"] = 0
    with pytest.raises(ValidationError):
        BlueprintPayload.model_validate(raw)

    stream["price_point"] = 99
    stream["churn_monthly"] = 1.5
    with pytest.raises(ValidationError):
        BlueprintPayload.model_validate(raw)


def test_nested_list_models() -> None:
    payload = _valid_payload()
    assert payload.cost_structure.team[0].role == "CEO/Founder"
    assert payload.cost_structure.team[0].hire_month == 0
    assert payload.identified_vulnerabilities[0].severity == "high"
