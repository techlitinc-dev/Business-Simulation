"""Generate the frozen golden-trace fixtures for the engine (T15).

Run once from backend/:
    python tests/fixtures/generate_golden_traces.py

The output JSON files are reviewed by hand against Appendix B's trace shape
(early burn, MRR ramp, runway trough) and then frozen as regression nets.
"""

import json
import random
from pathlib import Path

from app.engine.events import apply_event
from app.engine.loop import _customer_movement, _kpi_snapshot, run_simulation, tick
from app.engine.state import compile_blueprint

FIXTURES = Path(__file__).resolve().parent

EVT_001 = {
    "mechanical_impact": {
        "immediate": {
            "cac_delta_percent": 35,
            "churn_delta_percent": 15,
            "new_signups_delta_percent": -40,
            "team_morale_delta": -0.10,
            "cash_burn_delta_monthly": 0,
        }
    }
}


def _trace_kpis(result) -> dict[str, list[dict]]:
    return {"tick_logs": [{"month": t.month, "kpis": t.kpis} for t in result.tick_logs]}


def main() -> None:
    payload = json.loads((FIXTURES / "blueprint_golden.json").read_text())
    state = compile_blueprint(payload)

    baseline = run_simulation(state, 24, seed=42)
    (FIXTURES / "golden_trace_seed42.json").write_text(
        json.dumps(_trace_kpis(baseline), indent=2) + "\n"
    )

    # Inject evt_001 at the START of month 7 (before that month's tick), so the
    # -40% signups / +15% churn deltas show up in month 7's KPI snapshot and
    # months align 1:1 with the baseline trace.
    sim = state.snapshot()
    rng = random.Random(42)
    evt_logs = []
    prev = sim
    for m in range(1, 25):
        if m == 7:
            sim = apply_event(sim, EVT_001["mechanical_impact"], month=7)
        prev = sim
        sim = tick(sim, rng)
        new_customers, churned_customers = _customer_movement(prev, sim)
        evt_logs.append(
            {"month": m, "kpis": _kpi_snapshot(sim, new_customers, churned_customers)}
        )
        if sim.bankrupt:
            break
    (FIXTURES / "golden_trace_seed42_evt001.json").write_text(
        json.dumps({"tick_logs": evt_logs}, indent=2) + "\n"
    )
    print(f"evt001: months={len(evt_logs)} survived={not sim.bankrupt}")


if __name__ == "__main__":
    main()
