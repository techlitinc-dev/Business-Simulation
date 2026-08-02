# Phase 2 — Deterministic Simulation Engine

Build the pure-Python deterministic core (`backend/app/engine/`): state dataclasses, financial math, the monthly time-step loop, market dynamics, and event injection. No I/O, no DB, no network, no LLM calls — everything is seeded-deterministic and covered by pytest unit tests.

**Global rules for every task in this phase:**
- Python 3.12, standard library only (`dataclasses`, `random`, `math`, `enum`). Do NOT import FastAPI, SQLAlchemy, Pydantic, or anything from `app.core`/`app.db`/`app.models` inside `app/engine/`.
- All randomness comes from a `random.Random(seed)` instance created once per simulation run and threaded through — never the global `random` module.
- Money is `float` USD; rates (churn, margin, elasticity) are `float` fractions (e.g. `0.05` = 5%).
- Time step is monthly; month numbering starts at 1 for the first simulated month (month 0 is the initial state).
- Tests live in `backend/tests/unit/engine/`; shared fixtures in `backend/tests/fixtures/`. Run tests from `backend/` so imports resolve as `from app.engine.xxx import ...`.

---

## Task T11: Engine state dataclasses + blueprint→state compiler

**Description:** Create `backend/app/engine/state.py` with the engine's in-memory state model and a compiler that turns a Format-A blueprint payload (plain `dict`, as stored in `BlueprintVersion.payload`) into an initial `BusinessState`. Use stdlib `@dataclass` (NOT Pydantic — the engine is dependency-free). Define these classes:

- `TeamMember(role: str, salary_annual: float, hire_month: int)`
- `RevenueStream(name: str, pricing_model: str, price_point: float, projected_customers_month_12: int, ltv: float, cac: float, churn_monthly: float, customers: int = 0)`
- `FinancialState(cash: float, mrr: float, arr: float, monthly_burn: float, fixed_monthly: float, variable_per_unit: float, ar_days: int, ap_days: int, gross_margin: float, team: list[TeamMember], accounts_receivable: float = 0.0, accounts_payable: float = 0.0, profitable_streak: int = 0)`
- `MarketState(market_size: int, market_share: float, base_demand: float, price: float, reference_price: float, price_elasticity: float, seasonality: list[float], competitor_pressure: float, brand_sentiment: float)` — `seasonality` is exactly 12 monthly multipliers (default all `1.0`); `competitor_pressure` and `brand_sentiment` are fractions in `[0, 1]` with sentiment defaulting to `0.5`.
- `TriggerEvent(month: int, trigger: str, detail: str)` and a `Trigger(StrEnum)` with members `BANKRUPTCY`, `PROFITABILITY`, `FUNDING_NEED`, `MILESTONE`.
- `BusinessState(month: int, financials: FinancialState, market: MarketState, streams: list[RevenueStream], triggers_fired: list[TriggerEvent], active_event_effects: list[dict], bankrupt: bool = False)` with a `snapshot() -> BusinessState` method returning a `copy.deepcopy` of itself (used for per-month logging and Monte Carlo branching).

Then write `compile_blueprint(payload: dict) -> BusinessState` in the same file. The payload is Format A (spec §10):

```json
{
  "blueprint_version": "1.0",
  "business_profile": {"model_type": "SaaS", "stage": "Seed", "industry": "...", "geography": "..."},
  "revenue_engine": {"streams": [{"name": "...", "pricing_model": "Subscription",
      "price_point": 99, "projected_customers_month_12": 500, "ltv": 2400, "cac": 850, "churn_monthly": 0.05}]},
  "cost_structure": {"fixed_monthly": 35000, "variable_per_unit": 12,
      "team": [{"role": "CEO/Founder", "salary_annual": 80000, "hire_month": 0}], "burn_rate_month_1": 45000},
  "financials": {"starting_capital": 500000, "funding_rounds": [], "target_runway_months": 18},
  "identified_vulnerabilities": [],
  "simulation_parameters": {"time_step": "monthly", "monte_carlo_runs": 100, "random_seed": null}
}
```

Compiler rules: `FinancialState.cash = financials.starting_capital`; `monthly_burn = cost_structure.burn_rate_month_1`; `mrr = arr = 0` at month 0; `gross_margin` defaults to `0.8` (may be overridden by an optional `financials.gross_margin` key); `ar_days`/`ap_days` default `30` (optional `financials.ar_days` / `ap_days` keys). `MarketState.price` and `reference_price` come from the first stream's `price_point`; `base_demand` is derived as `projected_customers_month_12 / 12` (average monthly new customers implied by the blueprint); `market_size` defaults to `projected_customers_month_12 * 100`, `market_share` to `0.0`, `price_elasticity` to `-1.5` (optional `simulation_parameters.price_elasticity` key). The compiler must raise `ValueError` with a message naming the missing key when required keys are absent (`revenue_engine.streams` non-empty, `cost_structure`, `financials.starting_capital`). Also create `backend/app/engine/__init__.py` (empty) and `backend/tests/unit/engine/__init__.py` (empty).

**Acceptance criteria:**
- [ ] `compile_blueprint` on the fixture blueprint returns a `BusinessState` with `month == 0`, `financials.cash == 500000.0`, `financials.monthly_burn == 45000.0`, one `RevenueStream` with `customers == 0`, and empty `triggers_fired`
- [ ] Team members from `cost_structure.team` appear in `FinancialState.team` with salaries and hire months preserved
- [ ] Missing `financials.starting_capital` (or empty `streams`) raises `ValueError` naming the offending key
- [ ] `snapshot()` returns a deep copy: mutating the copy's `financials.cash` does not affect the original
- [ ] `backend/app/engine/` contains no imports from `fastapi`, `sqlalchemy`, `pydantic`, `app.core`, `app.db`, or `app.models` (assert with a test that walks the module source or via grep in CI)
- [ ] `MarketState.seasonality` is validated to length 12; wrong length raises `ValueError`

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/engine/test_state.py -v` (create `backend/tests/unit/engine/test_state.py` and fixture `backend/tests/fixtures/blueprint_golden.json` containing the Format-A example above)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `cd backend && python -c "import json; from app.engine.state import compile_blueprint; s = compile_blueprint(json.load(open('tests/fixtures/blueprint_golden.json'))); print(s)"` prints a populated state without errors

**Dependencies:** None (backend scaffold T02 only)

**Files likely touched:**
- `backend/app/engine/__init__.py`
- `backend/app/engine/state.py`
- `backend/tests/unit/engine/__init__.py`
- `backend/tests/unit/engine/test_state.py`
- `backend/tests/fixtures/blueprint_golden.json`

**Estimated scope:** M

---

## Task T12: Financial calculator (revenue, costs, cash flow, LTV/CAC, runway, MRR/ARR, NRR)

**Description:** Create `backend/app/engine/financials.py` — a module of pure functions implementing the financial math of the engine, with formulas taken verbatim from spec §5. No classes, no state mutation: every function takes plain numbers and/or engine dataclasses and returns numbers or a new `FinancialState`. Implement exactly these functions:

- `ltv(arpu: float, gross_margin: float, churn_monthly: float) -> float` — spec formula `(ARPU × Gross Margin) / Monthly Churn Rate`; raise `ValueError` if `churn_monthly <= 0`.
- `cac_payback_months(cac: float, arpu: float, gross_margin: float) -> float` — spec formula `CAC / (ARPU × Gross Margin)`.
- `runway_months(cash: float, monthly_burn: float) -> float` — spec formula `Cash Balance / Monthly Burn Rate`; return `math.inf` when `monthly_burn <= 0` (profitable or break-even).
- `net_revenue_retention(starting_mrr: float, expansion: float, contraction: float, churned: float) -> float` — spec formula `(Starting MRR + Expansion - Contraction - Churn) / Starting MRR`; raise `ValueError` if `starting_mrr <= 0`.
- `inventory_turnover(cogs: float, average_inventory: float) -> float` — spec formula `COGS / Average Inventory`.
- `cash_conversion_cycle(dio: float, dso: float, dpo: float) -> float` — spec formula `DIO + DSO - DPO`.
- `monthly_payroll(team: list[TeamMember], month: int) -> float` — sum of `salary_annual / 12` for members with `hire_month <= month`.
- `compute_revenue(new_customers: int, churned_customers: int, stream: RevenueStream) -> tuple[int, float]` — returns `(ending_customers, recognized_revenue)` where `recognized_revenue = ending_customers × stream.price_point` (subscription, in-month recognition); `ending_customers = max(0, stream.customers + new_customers - churned_customers)`.
- `compute_costs(fin: FinancialState, units_sold: int, marketing_spend: float, month: int) -> dict[str, float]` — returns `{"fixed": ..., "payroll": ..., "variable": ..., "operational": ..., "total": ...}` where `variable = variable_per_unit × units_sold` and `operational = marketing_spend` (spec §5 step 2: fixed + variable + operational).
- `apply_cash_flow(fin: FinancialState, revenue: float, total_costs: float) -> FinancialState` — returns a NEW `FinancialState` (use `dataclasses.replace`) applying spec §5 step 3: with Net-30 AR default, this month's revenue lands as cash next month, so `cash += previous month's accounts_receivable - total_costs` and the new `accounts_receivable = revenue` when `ar_days == 30`; when `ar_days == 0` cash recognizes immediately. Also updates `mrr = revenue`, `arr = revenue × 12`, and `monthly_burn = total_costs - revenue` (floored at 0 for reporting? No — keep signed; runway handles the sign).
- `burn_rate(revenue: float, total_costs: float) -> float` — `total_costs - revenue` (negative means profitable).

Document each public function with a one-line docstring naming the spec formula.

**Acceptance criteria:**
- [ ] `ltv(99, 0.8, 0.05) == 1584.0`; `ltv(..., churn_monthly=0)` raises `ValueError`
- [ ] `cac_payback_months(850, 99, 0.8)` ≈ `10.73` (within 0.01); `runway_months(500000, 45000)` ≈ `11.11`; `runway_months(100, -5) == math.inf`
- [ ] `net_revenue_retention(10000, 2000, 500, 1000) == 1.05`
- [ ] `monthly_payroll` ignores members with `hire_month > month` and includes them once `month >= hire_month`
- [ ] `apply_cash_flow` is pure: the input `FinancialState` is unchanged after the call, and with `ar_days=30` a month of $10k revenue / $45k costs nets `cash == starting_cash - 45000` with `accounts_receivable == 10000`
- [ ] `compute_costs` total equals `fixed + payroll + variable + operational` exactly

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/engine/test_financials.py -v` (create this file; use `pytest.approx` for float comparisons)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `cd backend && python -c "from app.engine.financials import ltv; print(ltv(99, 0.8, 0.05))"` prints `1584.0`

**Dependencies:** T11

**Files likely touched:**
- `backend/app/engine/financials.py`
- `backend/tests/unit/engine/test_financials.py`

**Estimated scope:** M

---

## Task T13: Monthly time-step loop + trigger checks

**Description:** Create `backend/app/engine/loop.py` implementing the deterministic monthly time-step loop from spec §5's 8-step core loop, plus the trigger checks. It orchestrates `financials.py` (T12) and `market.py` (T14, being built in parallel — import the function names below; if T14 isn't merged yet, these names are the contract). Public API:

- `@dataclass TickLog` with `month: int` and `kpis: dict[str, float]` (cash, mrr, arr, burn, runway, customers, revenue, costs, new_customers, churned_customers — spec §5 step 8).
- `@dataclass SimulationResult` with `final_state: BusinessState`, `tick_logs: list[TickLog]`, `triggers: list[TriggerEvent]`, `survived: bool`, `months_simulated: int`.
- `check_triggers(state: BusinessState) -> list[TriggerEvent]` implementing spec §5 step 5 exactly:
  - `Trigger.BANKRUPTCY` when `cash < 0` (v1 has no credit line — treat "no credit available" as always true); sets `state.bankrupt = True` and ends the run.
  - `Trigger.PROFITABILITY` when net income (`revenue - total_costs`) `> 0` for 3 consecutive months — track via `FinancialState.profitable_streak`.
  - `Trigger.FUNDING_NEED` when `runway_months(cash, burn) < 6` (and burn > 0). Fires at most once per run.
  - `Trigger.MILESTONE` for crossing 100 customers and for crossing $1M ARR; each milestone fires at most once per run.
- `tick(state: BusinessState, rng: random.Random, marketing_spend: float = 0.0) -> BusinessState` — one month, executing the 8 steps in spec order: (1) demand from `market.compute_demand(state.market, month)` then new customers `= round(demand × market_share_factor)` and churned `= round(customers × churn)`; (2) costs via `compute_costs`; (3) cash flow via `apply_cash_flow`; (4) update financial state (cash, burn, MRR/ARR, runway); (5) `check_triggers`; (6) apply active event effects via `events.apply_due_events(state, month)` (T15 contract — import lazily/optionally so T13 tests don't need T15); (7) market update via `market.update_market(state.market, rng, month)`; (8) build and return the new state with month incremented (the caller logs KPIs).
- `run_simulation(initial_state: BusinessState, months: int, seed: int, marketing_spend: float = 0.0) -> SimulationResult` — creates `rng = random.Random(seed)` ONCE, snapshots the initial state, loops `tick` for `months` months, records a `TickLog` per month, stops early on bankruptcy, and returns the result. `survived = not final_state.bankrupt`.

Determinism contract: same `(initial_state, months, seed, marketing_spend)` → byte-identical `SimulationResult` (compare via a `to_dict()` or by comparing all TickLog KPI dicts).

**Acceptance criteria:**
- [ ] `run_simulation(state, 24, seed=42)` on the golden fixture returns `months_simulated == 24`, 24 `TickLog` entries, and `survived is True` (fixture assumptions survive baseline)
- [ ] With `starting_capital` reduced to `50000` in the fixture, the run ends early: `bankrupt is True`, `Trigger.BANKRUPTCY` present in `triggers`, `months_simulated < 24`
- [ ] Two calls `run_simulation(state, 24, seed=42)` produce identical tick-by-tick KPIs; `seed=43` may differ but is itself reproducible
- [ ] `Trigger.FUNDING_NEED` fires exactly once in the fixture run, in the first month where runway < 6
- [ ] Profitability trigger: a fixture variant with tiny costs and instant customers fires `Trigger.PROFITABILITY` exactly at the 3rd consecutive profitable month
- [ ] No engine file performs I/O: `run_simulation` never touches disk, network, env vars, or the global random module (test: `random.seed(999)` before a run does not change the result)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/engine/test_loop.py -v` (create this file; include the determinism double-run test and the bankruptcy early-exit test)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `cd backend && python -m pytest tests/unit/engine -q` shows all engine tests green together (no cross-test state leakage)

**Dependencies:** T12

**Files likely touched:**
- `backend/app/engine/loop.py`
- `backend/tests/unit/engine/test_loop.py`

**Estimated scope:** M

---

## Task T14: Market dynamics (demand curve, price elasticity, seasonality, competitor pressure)

**Description:** Create `backend/app/engine/market.py` implementing the market side of spec §5 step 1 (`Demand = f(Market Size, Price, Competitor Prices, Brand Sentiment, Seasonality)`) and step 7 (market state update). Pure functions over `MarketState`; all stochasticity comes from the `random.Random` instance passed in. Implement:

- `compute_demand(market: MarketState, month: int) -> float` — the demand equation:

  ```
  seasonal      = market.seasonality[(month - 1) % 12]
  price_factor  = (market.price / market.reference_price) ** market.price_elasticity
  pressure      = 1.0 - market.competitor_pressure
  sentiment     = 0.5 + market.brand_sentiment        # range [0.5, 1.5]
  demand        = market.base_demand * seasonal * price_factor * pressure * sentiment
  ```

  Clamp the result to `[0, market.market_size]`.
- `price_change_effect(market: MarketState, new_price: float) -> MarketState` — returns a new `MarketState` (via `dataclasses.replace`) with `price = new_price`; demand impact flows through `compute_demand` via `price_factor` (elasticity `< 0` means higher price → lower demand; with default `-1.5`, a +10% price change cuts demand by ≈13.4%).
- `update_market(market: MarketState, rng: random.Random, month: int) -> MarketState` — spec §5 step 7: deterministic drift plus seeded noise. `competitor_pressure` drifts up `+0.002` per month (market matures) plus `rng.uniform(-0.005, 0.005)` noise, clamped to `[0, 0.8]`; `brand_sentiment` mean-reverts 10% toward `0.5` each month plus `rng.uniform(-0.01, 0.01)`, clamped to `[0, 1]`; `market_size` grows at a fixed 0.5%/month. Returns a new `MarketState`.
- `apply_competitor_shock(market: MarketState, pressure_delta: float, sentiment_delta: float) -> MarketState` — used by the event injector (T15) for competitor-type hurdles; adds the deltas and clamps to the same bounds as `update_market`.

Demand and elasticity semantics must match spec §5's revenue line: `Revenue = Demand × Price × Market Share × Conversion Rate` — in this engine `compute_demand` returns potential new customers per month, and the loop (T13) converts it into actual new customers.

**Acceptance criteria:**
- [ ] With `price == reference_price`, no seasonality (all 1.0), `competitor_pressure == 0`, `brand_sentiment == 0.5`: `compute_demand` returns exactly `base_demand`
- [ ] Raising price 10% with default elasticity reduces demand by a factor of `1.1 ** -1.5` (≈0.866, test with `pytest.approx`)
- [ ] `seasonality[6] = 2.0` doubles demand in months 7, 19 (July each year) and leaves other months unchanged
- [ ] `competitor_pressure = 0.5` halves demand; result never exceeds `market_size` and never goes below 0
- [ ] `update_market` with two `random.Random(42)` instances produces identical sequences over 24 months; values stay within the documented clamps every month
- [ ] `apply_competitor_shock(pressure_delta=0.3)` raises pressure by exactly 0.3 (clamped at 0.8) and does not mutate the input state

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/engine/test_market.py -v` (create this file)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `cd backend && python -c "from app.engine.market import compute_demand; from app.engine.state import MarketState, FinancialState; m = MarketState(50000, 0.0, 100.0, 99, 99, -1.5, [1.0]*12, 0.0, 0.5); print(compute_demand(m, 1))"` prints `100.0`

**Dependencies:** T12

**Files likely touched:**
- `backend/app/engine/market.py`
- `backend/tests/unit/engine/test_market.py`

**Estimated scope:** M

---

## Task T15: Event injector + golden-path engine tests (seeded 24-month trace)

**Description:** Create `backend/app/engine/events.py` — the deterministic bridge between AI-generated hurdles and engine physics — plus the golden-path test suite that pins the whole engine's behavior for 24 months. The event injector consumes the `mechanical_impact.immediate` block of a Format-B hurdle (spec §10, the only part the engine may read — narrative and cascading text are AI-side concerns):

```json
"mechanical_impact": {
  "immediate": {
    "cac_delta_percent": 35,
    "churn_delta_percent": 15,
    "new_signups_delta_percent": -40,
    "team_morale_delta": -0.10,
    "cash_burn_delta_monthly": 0
  }
}
```

Implement:

- `@dataclass ActiveEffect` with `remaining_months: int` and `deltas: dict[str, float]` (an applied event persists its `new_signups_delta_percent` / `churn_delta_percent` effects for `duration_months`, default 3, decaying linearly to 0).
- `validate_mechanical_impact(raw: dict) -> dict` — validates the `immediate` dict against the allowed key set `{cac_delta_percent, churn_delta_percent, new_signups_delta_percent, team_morale_delta, cash_burn_delta_monthly, cash_delta_one_time, price_delta_percent, competitor_pressure_delta, sentiment_delta}`; unknown keys are dropped (logged via `warnings.warn`), missing keys default to 0. **Clamp to physical possibility** (this is the anti-LLM-hallucination guardrail from plan.md Risks): each `*_delta_percent` clamped to `[-90, +200]`; `team_morale_delta` to `[-1.0, 1.0]`; `competitor_pressure_delta` to `[-0.8, 0.8]`; `sentiment_delta` to `[-1.0, 1.0]`.
- `apply_event(state: BusinessState, mechanical_impact: dict, month: int, duration_months: int = 3) -> BusinessState` — applies validated deltas: one-time `cash_delta_one_time` adjusts `financials.cash` immediately; `cash_burn_delta_monthly` adjusts `fixed_monthly`; `churn_delta_percent` adjusts each stream's `churn_monthly` multiplicatively, clamped to `[0.001, 0.95]`; `competitor_pressure_delta` / `sentiment_delta` go through `market.apply_competitor_shock`; `cac_delta_percent` adjusts each stream's `cac`, floored at `1.0`; percentage-based signup/churn effects that persist are appended to `state.active_event_effects` as an `ActiveEffect`. New state values must stay physically possible: churn ∈ `[0,1]`, price > 0, cash may go negative (bankruptcy is the loop's job), morale ∈ `[0,1]`.
- `apply_due_events(state: BusinessState, month: int) -> BusinessState` — called from loop step 6: decays each `ActiveEffect` by one month, recomputes the effective `new_signups_delta_percent` / `churn_delta_percent` modifiers the loop should use this month (expose them as `state.active_event_effects`), and drops expired effects.

Then write the **golden-path suite** in `backend/tests/unit/engine/test_golden_trace.py`: load `tests/fixtures/blueprint_golden.json`, run `run_simulation(state, 24, seed=42)`, and assert the FULL 24-month trace — expected values for cash, MRR, customers, and burn for every month stored in `tests/fixtures/golden_trace_seed42.json` (generate it once from the implementation, then review the numbers by hand against the Appendix B trace shape in the spec: early burn, MRR ramp, runway trough — and freeze it). Add a second golden test that injects the spec's evt_001 hurdle at month 7 (`cac_delta_percent=35, churn_delta_percent=15, new_signups_delta_percent=-40, team_morale_delta=-0.10`) and asserts the month-7..10 KPI deltas match a frozen `tests/fixtures/golden_trace_seed42_evt001.json`. These tests are the regression net for T47's coverage push and for any future engine refactor.

**Acceptance criteria:**
- [ ] `validate_mechanical_impact` drops unknown keys, defaults missing ones to 0, and clamps `cac_delta_percent=500` to `200` and `new_signups_delta_percent=-100` to `-90`
- [ ] `apply_event` with the spec's evt_001 immediate block raises every stream's `churn_monthly` by 15% (multiplicative), raises `cac` by 35%, and appends a 3-month `ActiveEffect` — and never mutates the input state
- [ ] Churn can never exceed `0.95` or go below `0.001` no matter how extreme the (clamped) input; morale stays in `[0, 1]`
- [ ] `apply_due_events` reduces `remaining_months` by 1 per call, scales the persistent deltas linearly (month 2 of 3 → 2/3 strength), and removes the effect when it reaches 0
- [ ] Golden trace test: 24-month run with `seed=42` matches `golden_trace_seed42.json` exactly for every month (cash to 2 decimal places); re-running produces identical output
- [ ] Golden event test: the evt_001 run matches `golden_trace_seed42_evt001.json` exactly, and month-7 customers are strictly lower than the baseline golden trace month-7 customers

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/engine -v` (create `test_events.py` and `test_golden_trace.py`; the whole engine suite must be green)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `cd backend && python -m timeit -s "import json; from app.engine.state import compile_blueprint; from app.engine.loop import run_simulation; s = compile_blueprint(json.load(open('tests/fixtures/blueprint_golden.json')))" "run_simulation(s.snapshot(), 24, 42)"` shows a 24-month run well under 100 ms (Checkpoint B gate)

**Dependencies:** T13, T14

**Files likely touched:**
- `backend/app/engine/events.py`
- `backend/tests/unit/engine/test_events.py`
- `backend/tests/unit/engine/test_golden_trace.py`
- `backend/tests/fixtures/golden_trace_seed42.json`
- `backend/tests/fixtures/golden_trace_seed42_evt001.json`

**Estimated scope:** M

---

## Checkpoint B

- [ ] Engine simulates 24 months from fixture blueprint in <100ms; identical seeds → identical traces; `pytest tests/unit/engine` green
