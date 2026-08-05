"""Hurdle generator tests (T23)."""

import json
from pathlib import Path

from app.agents.chronicle import Chronicle
from app.agents.hurdle_generator import HurdleGenerator, build_vital_signs
from app.agents.llm.base import MockProvider
from app.engine.loop import run_simulation
from app.engine.state import compile_blueprint
from app.schemas.hurdle import HurdleEvent

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _state_at_month(month: int):
    """Run the golden blueprint up to the given month and return the state + last kpis."""
    payload = json.loads((FIXTURES / "blueprint_golden.json").read_text())
    result = run_simulation(compile_blueprint(payload), month, seed=42)
    kpis = result.tick_logs[-1].kpis if result.tick_logs else {}
    return result.final_state, kpis


def _canned_hurdle(event_id: str = "evt_001", source_actor: str = "Competitor X") -> str:
    return json.dumps(
        {
            "event_id": event_id,
            "trigger_timing": "month 7",
            "category": "market",
            "narrative": {
                "title": "Competitor launches freemium",
                "story": "A rival undercuts pricing.",
                "source_actor": source_actor,
                "believability_score": 0.85,
            },
            "mechanical_impact": {
                "immediate": {"cac_delta_percent": 35, "churn_delta_percent": 15},
                "cascading": {"month 9": "churn stays elevated"},
            },
            "ai_game_master_note": "Single-stream concentration exposed.",
        }
    )


async def test_build_vital_signs_has_required_fields() -> None:
    state, kpis = _state_at_month(7)
    vital = build_vital_signs(state, kpis)
    for key in (
        "burn_rate",
        "runway_months",
        "cash_reserves",
        "cac",
        "ltv",
        "churn_monthly",
        "month",
    ):
        assert key in vital
    assert vital["month"] == 7
    assert vital["cac"] > 0


async def test_generate_returns_valid_hurdle_and_records_entry() -> None:
    state, kpis = _state_at_month(7)
    provider = MockProvider()
    provider.register("VITAL SIGNS", _canned_hurdle())

    chronicle = Chronicle()
    generator = HurdleGenerator(provider)
    hurdle = await generator.generate(state, kpis, chronicle, month=7)

    assert isinstance(hurdle, HurdleEvent)
    assert HurdleEvent.model_validate(hurdle.model_dump()) is not None
    assert hurdle.narrative.source_actor == "Competitor X"
    assert len(chronicle.entries) == 1
    assert chronicle.get_actor("Competitor X") is not None


async def test_chronicle_actor_carries_to_next_prompt() -> None:
    state, kpis = _state_at_month(7)
    provider = MockProvider()
    provider.register("VITAL SIGNS", _canned_hurdle())

    chronicle = Chronicle()
    generator = HurdleGenerator(provider)
    await generator.generate(state, kpis, chronicle, month=7)

    # Second run: capture the user prompt via a recording wrapper.
    prompts: list[str] = []

    class RecordingProvider(MockProvider):
        async def complete(self, system, user, **kwargs):
            prompts.append(user)
            return await super().complete(system, user, **kwargs)

    rec = RecordingProvider()
    rec.register("VITAL SIGNS", _canned_hurdle(event_id="evt_002"))
    gen2 = HurdleGenerator(rec)
    await gen2.generate(state, kpis, chronicle, month=8)

    assert any("Competitor X" in p for p in prompts)


async def test_clamping_accepts_wild_cac_delta() -> None:
    state, kpis = _state_at_month(7)
    canned = json.loads(_canned_hurdle())
    canned["mechanical_impact"]["immediate"]["cac_delta_percent"] = 9999
    provider = MockProvider()
    provider.register("VITAL SIGNS", json.dumps(canned))

    generator = HurdleGenerator(provider)
    hurdle = await generator.generate(state, kpis, Chronicle(), month=7)
    assert hurdle.mechanical_impact.immediate.cac_delta_percent == 200.0


async def test_repair_loop_recovers_invalid_hurdle() -> None:
    state, kpis = _state_at_month(7)
    provider = MockProvider()
    # Register repair match first (repair prompt contains "failed validation").
    provider.register("failed validation", _canned_hurdle(event_id="evt_repair"))
    provider.register("VITAL SIGNS", "{ not valid json")

    generator = HurdleGenerator(provider)
    hurdle = await generator.generate(state, kpis, Chronicle(), month=7)
    assert hurdle.event_id == "evt_repair"
