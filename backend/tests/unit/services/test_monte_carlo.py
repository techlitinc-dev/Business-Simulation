"""Monte Carlo worker tests (T27): aggregation + batch determinism."""

import json
from pathlib import Path

import fakeredis.aioredis
from app.workers.monte_carlo import (
    HURDLE_TEMPLATES,
    aggregate_results,
    run_monte_carlo_batch,
    run_one,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _blueprint() -> dict:
    return json.loads((FIXTURES / "blueprint_golden.json").read_text())


def test_aggregate_all_survive() -> None:
    outcomes = [
        {"seed": 1, "survived": True, "lifespan_months": 24, "kill_vector": None},
        {"seed": 2, "survived": True, "lifespan_months": 24, "kill_vector": None},
    ]
    result = aggregate_results(outcomes)
    assert result.n_runs == 2
    assert result.survival_rate == 1.0
    assert result.median_lifespan_months == 24
    assert result.kill_vectors == {}


def test_aggregate_all_die_at_month_0() -> None:
    outcomes = [
        {"seed": 1, "survived": False, "lifespan_months": 0, "kill_vector": "natural_causes"},
        {"seed": 2, "survived": False, "lifespan_months": 0, "kill_vector": "market"},
    ]
    result = aggregate_results(outcomes)
    assert result.survival_rate == 0.0
    assert result.median_lifespan_months == 0
    assert result.kill_vectors == {"natural_causes": 1, "market": 1}


def test_aggregate_n_runs_one() -> None:
    outcomes = [
        {"seed": 7, "survived": False, "lifespan_months": 11, "kill_vector": "financial"},
    ]
    result = aggregate_results(outcomes)
    assert result.n_runs == 1
    assert result.survival_rate == 0.0
    assert result.median_lifespan_months == 11
    assert result.p25_lifespan_months == 11
    assert result.p75_lifespan_months == 11
    assert result.kill_vectors == {"financial": 1}


def test_kill_vectors_sum_matches_failed_count() -> None:
    outcomes = [
        {
            "seed": i,
            "survived": i % 2 == 0,
            "lifespan_months": 12 + i,
            "kill_vector": None if i % 2 == 0 else "market",
        }
        for i in range(10)
    ]
    result = aggregate_results(outcomes)
    survived = sum(1 for o in outcomes if o["survived"])
    assert sum(result.kill_vectors.values()) == len(outcomes) - survived


def test_batch_deterministic() -> None:
    payload = _blueprint()
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    import asyncio

    async def _run() -> None:
        result_a, cancelled_a = await run_monte_carlo_batch(
            blueprint_payload=payload, base_seed=42, n_runs=5, months=24,
            run_id="run_a", redis=redis,
        )
        result_b, cancelled_b = await run_monte_carlo_batch(
            blueprint_payload=payload, base_seed=42, n_runs=5, months=24,
            run_id="run_b", redis=redis,
        )
        assert cancelled_a is False and cancelled_b is False
        assert result_a.model_dump(mode="json") == result_b.model_dump(mode="json")
        assert result_a.n_runs == 5

    asyncio.run(_run())


def test_batch_progress_and_no_llm() -> None:
    """Progress key climbs and no LLM provider call occurs (templates only)."""
    payload = _blueprint()
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    import asyncio

    async def _run() -> None:
        result, _ = await run_monte_carlo_batch(
            blueprint_payload=payload, base_seed=1, n_runs=4, months=24,
            run_id="run_prog", redis=redis,
        )
        raw = await redis.get("sim:run_prog:progress")
        assert raw is not None
        progress = json.loads(raw)
        assert progress["completed"] == 4
        assert progress["total"] == 4
        assert progress["percent"] == 100.0
        assert result.n_runs == 4
        # kill_vectors keyed by category, summing to the failed-run count.
        failed = sum(1 for s in result.runs_summary if not s.survived)
        assert sum(result.kill_vectors.values()) == failed

    asyncio.run(_run())


def test_cancel_flag_stops_batch() -> None:
    payload = _blueprint()
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    import asyncio

    async def _run() -> None:
        await redis.set("sim:run_c:control", "cancel")
        result, cancelled = await run_monte_carlo_batch(
            blueprint_payload=payload, base_seed=1, n_runs=100, months=24,
            run_id="run_c", redis=redis,
        )
        assert cancelled is True
        assert result.n_runs <= 1  # checked before the first sub-run

    asyncio.run(_run())


def test_run_one_shape() -> None:
    outcome = run_one(_blueprint(), seed=5, months=24)
    assert set(outcome.keys()) == {
        "seed", "survived", "lifespan_months", "kill_vector"
    }
    assert outcome["seed"] == 5
    assert 0 <= outcome["lifespan_months"] <= 24
    if not outcome["survived"]:
        allowed = {t["category"] for t in HURDLE_TEMPLATES} | {"natural_causes"}
        assert outcome["kill_vector"] in allowed
