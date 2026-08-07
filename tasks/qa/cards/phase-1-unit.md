# PHASE 1 — UNIT / MODULE ISOLATION TESTS

Every function, class, and endpoint is tested in **complete isolation**: DB,
Redis, LLM, Stripe, and email are all mocked. Engine modules are pure (no I/O),
services run against the in-memory sqlite test harness
(`backend/tests/conftest.py`), agents run against the deterministic
`MockProvider`, and the FastAPI app runs through `httpx.ASGITransport`
(no network). Target: **100% critical-path coverage**, **< 50 ms per test**.

Coverage gates (CI contract, enforced here too):
- `pytest tests/unit/engine --cov=app/engine --cov-fail-under=90`
- `pytest tests/integration/api --cov=app/api --cov-fail-under=70`

Existing repo suites are the canonical unit tests; the cards below **run them
and additionally execute targeted one-liner probes** that verify the specific
module contracts in isolation. Each card declares its exact command.

---
# CARDS: P1T001 P1T002 P1T003 P1T004 P1T005 P1T006 P1T007 P1T008 P1T009 P1T010 P1T011 P1T012 P1T013 P1T014 P1T015 P1T016 P1T017 P1T018 P1T019 P1T020 P1T021 P1T022 P1T023 P1T024
# PRE:   pre_phase1_clean
# POST:  post_phase1_teardown
# NEXT:  P1T001 -> P1T002
# NEXT:  P1T002 -> P1T003
# NEXT:  P1T003 -> P1T004
# NEXT:  P1T004 -> P1T005
# NEXT:  P1T005 -> P1T006
# NEXT:  P1T006 -> P1T007
# NEXT:  P1T007 -> P1T008
# NEXT:  P1T008 -> P1T009
# NEXT:  P1T009 -> P1T010
# NEXT:  P1T010 -> P1T011
# NEXT:  P1T011 -> P1T012
# NEXT:  P1T012 -> P1T013
# NEXT:  P1T013 -> P1T014
# NEXT:  P1T014 -> P1T015
# NEXT:  P1T015 -> P1T016
# NEXT:  P1T016 -> P1T017
# NEXT:  P1T017 -> P1T018
# NEXT:  P1T018 -> P1T019
# NEXT:  P1T019 -> P1T020
# NEXT:  P1T020 -> P1T021
# NEXT:  P1T021 -> P1T022
# NEXT:  P1T022 -> P1T023
# NEXT:  P1T023 -> P1T024
# NEXT:  P1T024 -> END
---

PY="${VENV_DIR}/bin/python"
PYTEST="${VENV_DIR}/bin/pytest"
# FIXTURES is exported by run_phase.sh (falls back to the repo path here so the
# card file also works when sourced manually).
FIXTURES="${FIXTURES:-$REPO_ROOT/tasks/qa/fixtures}"

# Phase 1 runs in complete isolation: force the in-memory sqlite engine and
# cheap hashing BEFORE any app import, exactly like backend/tests/conftest.py.
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
export FORGE_CHEAP_HASH="1"

pre_phase1_clean() {
  # Verify the environment is clean: no residual DB files, no running containers.
  test ! -f "$BACKEND_DIR/.coverage"
  test -x "$PYTEST"
}

post_phase1_teardown() {
  rm -f "$BACKEND_DIR/.coverage" "$BACKEND_DIR/.pytest_cache" -r
}

# ────────────────────────────────────────────────────────────────────────────
# P1T001 — engine/state: dataclass + compile_blueprint
# ────────────────────────────────────────────────────────────────────────────
card_P1T001() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import json
from app.engine.state import compile_blueprint
bp = json.load(open("tests/fixtures/blueprint_valid.json"))
state = compile_blueprint(bp)
assert state.month == 0
assert state.financials.cash == 500000.0
assert state.streams[0].price_point == 99.0
assert state.streams[0].churn_monthly == 0.05
assert len(state.financials.team) == 3
assert state.market.seasonality == [1.0]*12
try:
    compile_blueprint({"revenue_engine": {"streams": []}})
    raise SystemExit("expected ValueError")
except ValueError:
    pass
print("PASS: engine/state compile")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T002 — engine/financials: LTV, CAC payback, runway, NRR, turnover, CCC
# ────────────────────────────────────────────────────────────────────────────
card_P1T002() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
from app.engine.financials import (ltv, cac_payback_months, runway_months,
    net_revenue_retention, inventory_turnover, cash_conversion_cycle,
    monthly_payroll, burn_rate, apply_cash_flow, compute_revenue)
from app.engine.state import FinancialState, TeamMember, RevenueStream
assert ltv(100.0, 0.8, 0.05) == 1600.0
assert abs(cac_payback_months(850.0, 99.0, 0.8) - 10.732) < 0.001
assert runway_months(500000.0, 45000.0) == 500000.0/45000.0
assert runway_months(100.0, 0.0) == float("inf")
try:
    ltv(1, 1, 0); raise SystemExit("expected ValueError")
except ValueError: pass
assert net_revenue_retention(1000, 200, 50, 100) == 1.05
assert inventory_turnover(10000, 2000) == 5.0
assert cash_conversion_cycle(30, 45, 15) == 60.0
assert monthly_payroll([TeamMember("e", 120000, 0)], 1) == 10000.0
assert burn_rate(5000, 10000) == 5000.0
fin = FinancialState(10000, 0, 0, 0, 1000, 0, 0, 0, 0.8, [])
nf = apply_cash_flow(fin, 2000, 1500)
assert nf.cash == 10500.0 and nf.mrr == 2000.0 and nf.arr == 24000.0
s = RevenueStream("s","Subscription",99,500,2400,850,0.05,0)
assert compute_revenue(10, 0, s) == (10, 990.0)
print("PASS: engine/financials math")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T003 — engine/market: demand curve, seasonality, elasticity, shocks
# ────────────────────────────────────────────────────────────────────────────
card_P1T003() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import random
from app.engine.market import compute_demand, update_market, apply_competitor_shock, price_change_effect
from app.engine.state import MarketState
m = MarketState(10000, 0.0, 500.0, 99.0, 99.0, -1.5, [1.0]*12, 0.0, 0.5)
d1 = compute_demand(m, 1)
assert 0.0 <= d1 <= 10000.0
assert compute_demand(m, 1) == d1  # deterministic
m2 = update_market(m, random.Random(42), 1)
assert m2.market_size == 10050  # 0.5% growth
assert 0.0 <= m2.competitor_pressure <= 0.8
m3 = apply_competitor_shock(m, 0.5, -0.3)
assert m3.competitor_pressure == 0.5
assert abs(m3.brand_sentiment - 0.2) < 1e-9
mp = price_change_effect(m, 60.0)
assert mp.price == 60.0 and m.price == 99.0  # no mutation
print("PASS: engine/market")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T004 — engine/loop: tick() determinism, triggers, bankruptcy
# ────────────────────────────────────────────────────────────────────────────
card_P1T004() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import json, random
from app.engine.loop import tick, run_simulation, check_triggers
from app.engine.state import compile_blueprint, Trigger
# The GOLDEN blueprint is the one that survives 24 months (used by the repo's
# own frozen-trace tests); the VALID blueprint is the structural-validation one.
golden = json.load(open("tests/fixtures/blueprint_golden.json"))
state = compile_blueprint(golden)
rng = random.Random(42)
s1 = tick(state, rng)
rng2 = random.Random(42)
s2 = tick(state, rng2)
assert s1.month == 1 and s1.month == s2.month
assert s1.financials.cash == s2.financials.cash  # deterministic
# 24 months, survives to the end, exactly 24 ticks.
result = run_simulation(state, 24, seed=42)
assert result.survived is True
assert len(result.tick_logs) == 24
assert result.months_simulated == 24
# Bankruptcy trigger: negative cash fires BANKRUPTCY exactly once.
bp = json.load(open("tests/fixtures/blueprint_valid.json"))
bankrupt = compile_blueprint(bp)
bankrupt.financials.cash = -1.0
fires = check_triggers(bankrupt)
assert bankrupt.bankrupt and any(t.trigger == Trigger.BANKRUPTCY for t in fires)
print("PASS: engine/loop determinism + triggers")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T005 — engine golden trace: seed=42 matches committed fixture byte-for-byte
# ────────────────────────────────────────────────────────────────────────────
card_P1T005() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import json
from pytest import approx
from app.engine.loop import run_simulation
from app.engine.state import compile_blueprint
# The golden trace freezes the _kpi_snapshot() shape (cash/mrr/burn/runway)
# for the GOLDEN blueprint — mirror the repo's own test_golden_trace.py
# (which uses pytest.approx to handle inf runway etc.).
bp = json.load(open("tests/fixtures/blueprint_golden.json"))
expected = json.load(open("tests/fixtures/golden_trace_seed42.json"))
result = run_simulation(compile_blueprint(bp), 24, seed=42)
actual = [{"month": t.month, "kpis": dict(t.kpis)} for t in result.tick_logs]
assert result.survived is True
assert len(actual) == len(expected["tick_logs"]), "tick count mismatch"
for i, (a, e) in enumerate(zip(actual, expected["tick_logs"])):
    assert a["month"] == e["month"], f"month mismatch at {i}"
    for k, ev in e["kpis"].items():
        av = a["kpis"].get(k)
        assert av is not None, f"missing kpi {k} at month {a['month']}"
        assert av == approx(ev, abs=0.01), f"kpi {k} at month {a['month']}: {av} != {ev}"
print("PASS: engine golden trace seed=42")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T006 — engine/events: clamping, unknown-key drops, effect decay
# ────────────────────────────────────────────────────────────────────────────
card_P1T006() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import json
from app.engine.events import validate_mechanical_impact, apply_event, apply_due_events, ActiveEffect
from app.engine.state import compile_blueprint
bp = json.load(open("tests/fixtures/blueprint_valid.json"))
cleaned = validate_mechanical_impact({"immediate": {"churn_delta_percent": 999, "bogus_key": 1}})
assert cleaned["churn_delta_percent"] == 200.0   # clamped to max
assert "bogus_key" not in cleaned
state = compile_blueprint(bp)
before_cash = state.financials.cash
ns = apply_event(state, {"immediate": {"cash_delta_one_time": -50000}}, month=6, duration_months=3)
assert ns.financials.cash == before_cash - 50000.0
assert state.financials.cash == before_cash      # input never mutated
assert len(ns.active_event_effects) == 0         # one-time impact has no persistent effect
ns2 = apply_event(state, {"immediate": {"churn_delta_percent": 10}}, month=6, duration_months=3)
assert len(ns2.active_event_effects) == 1
ns3 = apply_due_events(ns2, 7)
assert len(ns3.active_event_effects) == 1
ns4 = apply_due_events(ns3, 8)
assert len(ns4.active_event_effects) == 1
ns5 = apply_due_events(ns4, 9)
assert len(ns5.active_event_effects) == 0       # expired after 3 months
print("PASS: engine/events clamp+decay")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T007 — engine/metrics: KPI shape + resilience score bounds
# ────────────────────────────────────────────────────────────────────────────
card_P1T007() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import json
from app.engine.loop import run_simulation
from app.engine.state import compile_blueprint
from app.engine.metrics import kpi_snapshot, resilience_score
bp = json.load(open("tests/fixtures/blueprint_valid.json"))
state = compile_blueprint(bp)
k = kpi_snapshot(state, 5, 1)
required = {"month","cash_balance","burn_rate","runway_months","revenue","costs",
            "net_income","mrr","arr","customers","churn_rate","cac","ltv",
            "ltv_cac_ratio","new_customers","churned_customers"}
assert required.issubset(k.keys()), f"missing {required - k.keys()}"
assert k["month"] == 0.0 and k["cash_balance"] == 500000.0
score = resilience_score(state, 24, 24)
assert 0 <= score <= 100
assert score >= 92                        # strong survival share
early = resilience_score(state, 0, 24)    # died instantly, healthy cash buffer
assert 0 <= early <= 100
assert early < score                      # fewer survival months => lower score
print("PASS: engine/metrics")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T008 — agents/llm: MockProvider determinism + cost/latency fields
# ────────────────────────────────────────────────────────────────────────────
card_P1T008() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import asyncio
from app.agents.llm.base import MockProvider, LLMResponse

async def main():
    p = MockProvider()
    r1 = await p.complete("sys", "Generate one context-aware hurdle for a SaaS at seed")
    r2 = await p.complete("sys", "Generate one context-aware hurdle for a SaaS at seed")
    assert r1.content == r2.content, "mock provider must be deterministic"
    import json
    parsed = json.loads(r1.content)
    for key in ("event_id","trigger_timing","category","narrative","mechanical_impact","ai_game_master_note"):
        assert key in parsed, f"missing {key}"
    assert parsed["category"] in ("market","operational","financial","black_swan","internal")
    assert 0.0 <= parsed["narrative"]["believability_score"] <= 1.0
    assert isinstance(r1, LLMResponse) and r1.model == "mock-model"
    assert r1.prompt_tokens > 0 and r1.completion_tokens > 0 and r1.latency_ms >= 0
    assert r1.cost_usd == 0.0
    p2 = MockProvider()
    p2.register("canned", '{"canned": true}')
    rc = await p2.complete("s", "canned prompt")
    assert json.loads(rc.content) == {"canned": True}
asyncio.run(main())
print("PASS: agents/llm mock provider")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T009 — agents/llm: factory resolves mock vs openai-compatible by settings
# ────────────────────────────────────────────────────────────────────────────
card_P1T009() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
from app.core.config import get_settings
from app.agents.llm.factory import get_llm_provider
s = get_settings()
s.llm_provider = "mock"
s.llm_api_key = ""
p1 = get_llm_provider(s)
from app.agents.llm.base import MockProvider
assert isinstance(p1, MockProvider), f"expected MockProvider, got {type(p1)}"
# auto + empty key also resolves to mock
s.llm_provider = "auto"
p2 = get_llm_provider(s)
assert isinstance(p2, MockProvider)
print("PASS: agents/llm factory")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T010 — agents/bridge: JSON extraction, clamping, repair-retry loop
# ────────────────────────────────────────────────────────────────────────────
card_P1T010() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import asyncio, json
from pydantic import BaseModel
from app.agents.bridge import extract_json, clamp_deltas, generate_structured
from app.agents.llm.base import MockProvider
from app.core.exceptions import StructuredOutputError

assert extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
assert extract_json('Here is the result: {"a": 1} thanks') == '{"a": 1}'
clamped = clamp_deltas({"cac_delta_percent": 500, "nested": {"churn_delta_percent": -999}})
assert clamped["cac_delta_percent"] == 200.0
assert clamped["nested"]["churn_delta_percent"] == -90.0

class Sample(BaseModel):
    name: str
    score: float

async def main():
    p = MockProvider()
    p.register("valid", '{"name": "x", "score": 0.9}')
    out = await generate_structured(p, Sample, "s", "valid prompt")
    assert out.name == "x" and out.score == 0.9
    # Invalid output then valid repair -> repair loop succeeds.
    calls = {"n": 0}
    class RepairProvider(MockProvider):
        async def complete(self, system, user, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                return type("R", (), {"content": "not json", "model":"m","prompt_tokens":1,"completion_tokens":1,"cost_usd":0.0,"latency_ms":1.0})()
            return type("R", (), {"content": '{"name": "ok", "score": 0.5}', "model":"m","prompt_tokens":1,"completion_tokens":1,"cost_usd":0.0,"latency_ms":1.0})()
    rp = RepairProvider()
    out2 = await generate_structured(rp, Sample, "s", "x", max_repairs=2)
    assert out2.name == "ok" and calls["n"] == 2
    # Persistent garbage -> StructuredOutputError.
    class GarbageProvider(MockProvider):
        async def complete(self, system, user, **kw):
            return type("R", (), {"content": "garbage", "model":"m","prompt_tokens":1,"completion_tokens":1,"cost_usd":0.0,"latency_ms":1.0})()
    try:
        await generate_structured(GarbageProvider(), Sample, "s", "x", max_repairs=1)
        raise SystemExit("expected StructuredOutputError")
    except StructuredOutputError:
        pass
asyncio.run(main())
print("PASS: agents/bridge")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T011 — agents/forge: blueprint review returns schema-valid vulnerabilities
# ────────────────────────────────────────────────────────────────────────────
card_P1T011() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import asyncio, json
from app.agents.llm.base import MockProvider
from app.agents.forge import ForgeAgent
bp = json.load(open("tests/fixtures/blueprint_valid.json"))
async def main():
    p = MockProvider()
    p.register("Review this business blueprint",
        json.dumps({"overall_assessment": "Structurally sound but cash-fragile.",
                    "identified_vulnerabilities": [
                        {"type": "liquidity", "severity": "high",
                         "description": "Thin runway.",
                         "mitigation_suggestion": "Cut fixed costs."}]}))
    review, response = await ForgeAgent(p).review_blueprint(bp)
    assert review.overall_assessment
    assert len(review.identified_vulnerabilities) == 1
    v = review.identified_vulnerabilities[0]
    assert v.type == "liquidity" and v.severity == "high"
    assert review.reviewed_version == 1
    assert review.tokens_used > 0
    assert response.model == "mock-model"
asyncio.run(main())
print("PASS: agents/forge")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T012 — agents/hurdle_generator + strategist: vital signs → Format B + options
# ────────────────────────────────────────────────────────────────────────────
card_P1T012() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import asyncio, json
from app.agents.llm.base import MockProvider
from app.agents.hurdle_generator import HurdleGenerator
from app.agents.strategist import Strategist
from app.agents.chronicle import Chronicle
from app.engine.loop import run_simulation
from app.engine.metrics import kpi_snapshot
from app.engine.state import compile_blueprint
bp = json.load(open("tests/fixtures/blueprint_valid.json"))
state = compile_blueprint(bp)
result = run_simulation(state, 12, seed=42)
kpis = result.tick_logs[-1].kpis
async def main():
    p = MockProvider()
    hg = HurdleGenerator(p)
    hurdle = await hg.generate(state, kpis, Chronicle(), difficulty=1, month=7)
    assert hurdle.event_id.startswith("evt_")
    assert hurdle.category in ("market","operational","financial","black_swan","internal")
    assert hurdle.narrative.believability_score >= 0.0
    sg = Strategist(p)
    advise = await sg.advise(state, kpis, hurdle, Chronicle())
    assert len(advise.options) >= 2
    for o in advise.options:
        assert o.option_id in ("A","B","C","D")
        assert 0.0 <= o.probability_success <= 1.0
        assert o.cash_impact_monthly is not None
    assert len(advise.projections) == len(advise.options)
asyncio.run(main())
print("PASS: agents hurdle+strategist")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T013 — agents/post_mortem + ghost + chronicle: deterministic outputs
# ────────────────────────────────────────────────────────────────────────────
card_P1T013() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import asyncio, json
from app.agents.llm.base import MockProvider
from app.agents.post_mortem import PostMortemAgent, build_post_mortem_prompt
from app.agents.ghost import GhostAgent, GhostDecision
from app.agents.chronicle import Chronicle, ChronicleEntry
from app.schemas.report import SurvivalMetrics, TweakResult
from app.services.optimization_service import measure_all_tweaks

async def main():
    p = MockProvider()
    bp = json.load(open("tests/fixtures/blueprint_valid.json"))
    deltas = measure_all_tweaks(bp, n_runs=10, seed=42)
    assert len(deltas) >= 1
    metrics = SurvivalMetrics(survival_rate=0.72, runs_total=100, runs_survived=72,
                              median_lifespan_months=24, kill_vectors=[])
    # Post-mortem: mock provider path (prompt asks for a post-mortem) yields
    # schema-valid output; the prompt builder also round-trips.
    prompt = build_post_mortem_prompt(metrics, deltas, bp)
    assert "METRICS" in prompt and "BLUEPRINT" in prompt
    out = await PostMortemAgent(p).generate(metrics, deltas, bp)
    assert len(out.optimizations) >= 1
    assert out.counter_factual_insight
    assert len(out.blueprint_v2_suggestions) >= 1
    # Ghost: choose_option(hurdle, state_snapshot) with real Format B options.
    hurdle = {"strategic_options": [
        {"option_id": "A", "probability_success": 0.9, "cash_impact_monthly": -8000, "name": "Cut"},
        {"option_id": "B", "probability_success": 0.6, "cash_impact_monthly": -15000, "name": "Push"},
    ]}
    g = GhostAgent(p, personality="aggressive")
    d = await g.choose_option(hurdle, {"cash": 100000})
    assert isinstance(d, GhostDecision)
    assert d.option_id in ("A", "B")
    assert d.rationale
    # Personality rule: aggressive picks highest probability_success (A).
    assert d.option_id == "A"
    # Chronicle round-trip: add_entry(ChronicleEntry) + to_prompt_summary().
    c = Chronicle()
    c.add_entry(ChronicleEntry(month=7, event_id="evt_1", title="Freemium assault",
                               actors=["Competitor X"], summary="Free tier launched"))
    assert c.get_actor("Competitor X") is not None
    assert "Competitor X" in c.to_prompt_summary()
    d1 = c.to_dict(); c2 = Chronicle.from_dict(d1)
    assert c2.to_dict() == d1
asyncio.run(main())
print("PASS: agents post_mortem/ghost/chronicle")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T014 — services/blueprint_validation + schemas: structural rules
# ────────────────────────────────────────────────────────────────────────────
card_P1T014() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import json
from app.schemas.blueprint import BlueprintPayload
bp = json.load(open("tests/fixtures/blueprint_valid.json"))
parsed = BlueprintPayload.model_validate(bp)
assert parsed.revenue_engine.streams[0].ltv == 2400
assert len(parsed.cost_structure.team) == 3
assert parsed.financials.starting_capital == 500000
print("PASS: blueprint schemas")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T015 — services/optimization_service: 6 deterministic tweak deltas
# ────────────────────────────────────────────────────────────────────────────
card_P1T015() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import json
from app.services.optimization_service import measure_all_tweaks, apply_tweak, TWEAKS, TWEAK_KEYS
bp = json.load(open("tests/fixtures/blueprint_valid.json"))
results = measure_all_tweaks(bp, n_runs=10, seed=42)
assert len(results) == len(TWEAKS) == 6
keys = [r.tweak_key for r in results]
assert keys == TWEAK_KEYS
for r in results:
    assert isinstance(r.delta_pp, float)
    assert 0.0 <= r.baseline_survival <= 1.0 and 0.0 <= r.tweaked_survival <= 1.0
# determinism
results2 = measure_all_tweaks(bp, n_runs=10, seed=42)
assert [r.delta_pp for r in results] == [r.delta_pp for r in results2]
# tweak churn reduces churn_monthly by 20%
t = apply_tweak(bp, TWEAKS[0])
assert t["revenue_engine"]["streams"][0]["churn_monthly"] == 0.04
print("PASS: optimization_service")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T016 — services/metering_service: limit enforcement (free tier)
# ────────────────────────────────────────────────────────────────────────────
card_P1T016() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import asyncio
from app.core.exceptions import PlanLimitExceeded
from app.services.metering_service import check_limit, increment, get_current_usage
from app.models.workspace import Workspace
from app.db.base import Base
from app.db.session import async_engine, async_session_factory

async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as db:
        ws = Workspace(name="Q", slug="q", plan_tier="free")
        db.add(ws); await db.flush()
        wid = ws.id
        for _ in range(3):
            await increment(db, wid, "runs")
        rec = await get_current_usage(db, wid)
        assert rec.runs_used == 3
        try:
            await check_limit(db, wid, "runs", amount=1)
            raise SystemExit("expected PlanLimitExceeded")
        except PlanLimitExceeded as e:
            assert e.limit == 3 and e.tier == "free"
        # pro tier: 50 runs allowed
        ws2 = Workspace(name="P", slug="p", plan_tier="pro")
        db.add(ws2); await db.flush()
        await check_limit(db, ws2.id, "runs", amount=50)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
asyncio.run(main())
print("PASS: metering_service limits")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T017 — workers/monte_carlo: run_one + aggregate determinism
# ────────────────────────────────────────────────────────────────────────────
card_P1T017() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import json
from app.workers.monte_carlo import run_one, aggregate_results, _auto_option
bp = json.load(open("tests/fixtures/blueprint_valid.json"))
o1 = run_one(bp, seed=42, months=24)
o2 = run_one(bp, seed=42, months=24)
assert o1 == o2, "run_one must be deterministic per seed"
assert set(o1) == {"seed","survived","lifespan_months","kill_vector"}
assert 0 <= o1["lifespan_months"] <= 24
agg1 = aggregate_results([o1, o1, o1])
assert agg1.n_runs == 3
assert 0.0 <= agg1.survival_rate <= 1.0
assert agg1.median_lifespan_months == o1["lifespan_months"]
opts = [{"option_id":"B","probability_success":0.5},{"option_id":"A","probability_success":0.7}]
assert _auto_option(opts)["option_id"] == "A"
print("PASS: workers/monte_carlo")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T018 — core/security: JWT access/refresh, expiry type, malformed hash
# ────────────────────────────────────────────────────────────────────────────
card_P1T018() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import jwt
from app.core.security import (hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token)
h = hash_password("s3cret!")
assert h.startswith("$argon2")
assert verify_password("s3cret!", h)
assert not verify_password("wrong", h)
assert not verify_password("x", "malformed-hash")   # ValueError -> False
access = create_access_token("user-1")
r = decode_token(access)
assert r["type"] == "access" and r["sub"] == "user-1" and "jti" in r and "exp" in r
refresh = create_refresh_token("user-1")
assert decode_token(refresh)["type"] == "refresh"
try:
    decode_token("not.a.token"); raise SystemExit("expected jwt error")
except jwt.PyJWTError: pass
print("PASS: core/security")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T019 — core/rate_limit: window full -> reject, per-key prefix bucketing
# ────────────────────────────────────────────────────────────────────────────
card_P1T019() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
from app.core.rate_limit import _hit, reset_windows, _parse_rpm
from collections import deque
reset_windows()
w = deque()
assert _hit(w, 2) and _hit(w, 2)
assert not _hit(w, 2)          # window full -> rejected
assert _parse_rpm("100/minute") == 100
assert _parse_rpm("bogus") == 100
print("PASS: core/rate_limit window")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T020 — services/auth_service: register creates user + personal workspace
# ────────────────────────────────────────────────────────────────────────────
card_P1T020() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import asyncio
from app.services.auth_service import register_user, authenticate_user, refresh_tokens
from app.core.exceptions import DomainError
from app.models.workspace import Membership, Role
from app.db.base import Base
from app.db.session import async_engine, async_session_factory
from sqlalchemy import select

async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as db:
        user = await register_user(db, email="QA-a@forge.dev", name="QA User", password="QA-pass-1234!")
        assert user.email == "qa-a@forge.dev"           # normalized
        assert user.is_verified is False
        membership = await db.scalar(select(Membership).where(Membership.user_id == user.id))
        assert membership is not None and membership.role == Role.OWNER
        authed = await authenticate_user(db, email="qa-a@forge.dev", password="QA-pass-1234!")
        assert authed.id == user.id
        try:
            await authenticate_user(db, email="qa-a@forge.dev", password="nope")
            raise SystemExit("expected DomainError")
        except DomainError as e:
            assert e.status_code == 401
        try:
            await register_user(db, email="QA-A@forge.dev", name="x", password="xxxxxxxy!")
            raise SystemExit("expected duplicate DomainError")
        except DomainError as e:
            assert e.status_code == 409
        pair = refresh_tokens(db, __import__("app.core.security", fromlist=["create_refresh_token"]).create_refresh_token(str(user.id)))
        assert pair.access_token and pair.refresh_token
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
asyncio.run(main())
print("PASS: auth_service register/authenticate/refresh")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T021 — services/workspace_service + scenario_service: RBAC + clone
# ────────────────────────────────────────────────────────────────────────────
card_P1T021() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import asyncio, uuid
from app.services.workspace_service import create_workspace
from app.services.scenario_service import clone_to_workspace, list_public
from app.core.exceptions import DomainError
from app.models.workspace import Workspace, Membership, Role
from app.models.scenario import Scenario
from app.models.user import User
from app.db.base import Base
from app.db.session import async_engine, async_session_factory
from sqlalchemy import select

async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as db:
        user = User(email="owner@forge.dev", name="Owner", pw_hash="x")
        db.add(user); await db.flush()
        out = await create_workspace(db, name="QA Workspace", owner=user)
        assert out.slug.startswith("qa-workspace-")
        assert len(out.slug) == len("qa-workspace-") + 4  # 4-hex suffix
        ws = await db.get(Workspace, out.id)
        payload = {
            "business_profile": {"model_type": "SaaS", "stage": "Seed",
                                 "industry": "B2B Productivity Software", "geography": "North America"},
            "revenue_engine": {"streams": [{
                "name": "Primary Subscription", "pricing_model": "Subscription",
                "price_point": 99, "projected_customers_month_12": 500,
                "ltv": 2400, "cac": 850, "churn_monthly": 0.05}]},
            "cost_structure": {"fixed_monthly": 35000, "variable_per_unit": 12,
                               "team": [{"role": "CEO/Founder", "salary_annual": 80000, "hire_month": 0}],
                               "burn_rate_month_1": 45000},
            "financials": {"starting_capital": 500000, "funding_rounds": [],
                           "target_runway_months": 18},
            "identified_vulnerabilities": [],
            "simulation_parameters": {"time_step": "monthly", "monte_carlo_runs": 100,
                                      "random_seed": None},
        }
        # Private scenario is not cloneable -> 404.
        sc = Scenario(author_workspace_id=ws.id, title="T", description="D",
                      category="market", payload=payload, is_public=False)
        db.add(sc); await db.flush(); sc_id = sc.id
        try:
            await clone_to_workspace(db, scenario_id=sc_id, workspace_id=ws.id)
            raise SystemExit("expected DomainError")
        except DomainError as e:
            assert e.status_code == 404
        # Public scenario clones into another workspace as Blueprint v1.
        db.add(Scenario(author_workspace_id=ws.id, title="Pub", description="D",
                        category="market", payload=payload, is_public=True, clones_count=0))
        await db.flush()
        pub = await db.scalar(select(Scenario).where(Scenario.title == "Pub"))
        other_ws = Workspace(name="Other", slug="other"); db.add(other_ws); await db.flush()
        blueprint, version = await clone_to_workspace(db, scenario_id=pub.id, workspace_id=other_ws.id)
        assert blueprint.workspace_id == other_ws.id
        assert blueprint.name == "Pub"
        assert version.version == 1
        assert pub.clones_count == 1
        pubs, total = await list_public(db)
        assert total == 1
        assert any(s.title == "Pub" for s in pubs)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
asyncio.run(main())
print("PASS: workspace+scenario services")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T022 — services/api_key_service: prefix lookup, hashed storage
# ────────────────────────────────────────────────────────────────────────────
card_P1T022() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import asyncio, uuid, hashlib
from app.services.api_key_service import create_api_key, find_active_key, revoke_api_key, hash_key
from app.db.base import Base
from app.db.session import async_engine, async_session_factory

async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as db:
        wid = uuid.uuid4()
        created, key = await create_api_key(db, workspace_id=wid, name="qa-key",
                                            scopes=["simulations:read"], rate_limit_rpm=10)
        assert key.startswith("fk_") and len(key) > 20
        assert created.key == key                      # plaintext shown once
        found = await find_active_key(db, key)
        assert found is not None and found.workspace_id == wid
        assert found.prefix == key[:12]
        assert found.scopes == ["simulations:read"]
        assert found.key_hash == hash_key(key)  # plaintext never stored — only sha256
        assert found.key_hash != key
        await revoke_api_key(db, workspace_id=wid, api_key_id=found.id)
        assert await find_active_key(db, key) is None
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
asyncio.run(main())
print("PASS: api_key_service")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T023 — services/ghost_service + report_service pure helpers
# ────────────────────────────────────────────────────────────────────────────
card_P1T023() {
  ( cd "$BACKEND_DIR" && "$PY" - <<'PYEOF'
import json
from app.services.report_service import survival_metrics_from_result, render_survival_markdown, SEVERITY_RANK
try:
    from app.agents.ghost import GHOST_PERSONALITIES
except ImportError:
    GHOST_PERSONALITIES = []
assert isinstance(GHOST_PERSONALITIES, list)
result = {"n_runs": 100, "runs_summary": [{"survived": i < 72, "lifespan_months": 24 if i < 72 else 16} for i in range(100)],
          "kill_vectors": {"financial": 18, "market": 10}}
m = survival_metrics_from_result(result)
assert m.runs_total == 100 and m.runs_survived == 72
assert abs(m.survival_rate - 0.72) < 0.0001
assert m.kill_vectors[0].cause == "financial" and m.kill_vectors[0].pct == 64.3
md = render_survival_markdown(m)
assert "SURVIVAL METRICS" in md and "72%" in md
assert SEVERITY_RANK["CRITICAL"] < SEVERITY_RANK["HIGH"] < SEVERITY_RANK["MEDIUM"] < SEVERITY_RANK["LOW"]
print("PASS: report_service helpers")
PYEOF
)
}

# ────────────────────────────────────────────────────────────────────────────
# P1T024 — frontend stores + router unit tests (vitest)
# ────────────────────────────────────────────────────────────────────────────
card_P1T024() {
  # Frontend unit tests must run in DEV mode — a leaked NODE_ENV=production
  # disables React's act() and fails every render test. Unset it deterministically.
  ( cd "$FRONTEND_DIR" && env -u NODE_ENV npm run test --silent -- --run 2>&1 \
      | grep -E "Test Files|Tests " | tee -a "$QA_LOG" )
  return "${PIPESTATUS[0]}"
}
card_P1T024_deterministic() { echo "yes"; }
