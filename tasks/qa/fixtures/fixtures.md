# Mock / Fixture Data Definitions (Deliverable C)

Every fixture below is a **file on disk** or an **inline literal** that test
cards reference verbatim. Deterministic: the same fixture + same seed always
yields the same engine trace (proven by `backend/tests/unit/engine/test_golden_trace.py`
and `tests/fixtures/golden_trace_seed42.json`).

## C.1 Canonical user fixtures

| Fixture | Value | Used by |
|---|---|---|
| `USER_A_EMAIL` | `qa-a@forge.dev` | P1T020, P2T001, P2T003, P3T001+ |
| `USER_A_PASSWORD` | `QA-pass-1234!` | all auth paths |
| `USER_B_EMAIL` | `qa-b@forge.dev` | P2T003, P2T004, P3T008, P5T007 |
| `USER_B_PASSWORD` | `QA-pass-5678!` | all auth paths |
| `ADMIN_EMAIL` | `qa-admin@forge.dev` | P2T013, P5T011, P5T012 |
| `ADMIN_PASSWORD` | `QA-admin-0001!` | admin endpoints |
| `DEMO_EMAIL` / `DEMO_PASSWORD` | `demo@forge.dev` / `demo-password-123` | P3T001, P6T003 (seed) |
| `WORKSPACE_NAME` | `QA Workspace` | created in P2T001 |
| `WORKSPACE_SLUG` | `qa-workspace` | idempotency checks |

## C.2 Format A blueprint payload (identical to `tests/fixtures/blueprint_valid.json`)

> Both fixture JSONs are copied verbatim into this directory (`fixtures/`):
> `blueprint_valid.json` (structural validation) and `blueprint_golden.json`
> (the profile that survives all 24 months at every seed). Cards that assert a
> baseline **completes** MUST use `blueprint_golden.json`; `blueprint_valid.json`
> dies at month 12 at every seed (see P1T004/P1T005).

```json
{
  "blueprint_version": "1.0",
  "business_profile": {
    "model_type": "SaaS", "stage": "Seed",
    "industry": "B2B Productivity Software", "geography": "North America"
  },
  "revenue_engine": {
    "streams": [{
      "name": "Primary Subscription", "pricing_model": "Subscription",
      "price_point": 99, "projected_customers_month_12": 500,
      "ltv": 2400, "cac": 850, "churn_monthly": 0.05
    }]
  },
  "cost_structure": {
    "fixed_monthly": 35000, "variable_per_unit": 12,
    "team": [
      {"role": "CEO/Founder", "salary_annual": 80000, "hire_month": 0},
      {"role": "Lead Developer", "salary_annual": 120000, "hire_month": 0},
      {"role": "Sales Rep", "salary_annual": 70000, "hire_month": 3}
    ],
    "burn_rate_month_1": 45000
  },
  "financials": {
    "starting_capital": 500000, "funding_rounds": [], "target_runway_months": 18
  },
  "identified_vulnerabilities": [{
    "type": "liquidity", "severity": "high",
    "description": "Burn rate exceeds starting capital runway at current growth assumptions.",
    "mitigation_suggestion": "Reduce fixed costs by 20% or accelerate revenue to Month 4."
  }],
  "simulation_parameters": { "time_step": "monthly", "monte_carlo_runs": 100, "random_seed": null }
}
```

Validated by `BlueprintPayload` (Pydantic). The **golden-trace** pair is
`tests/fixtures/blueprint_golden.json` (the one that survives 24 months) with
`golden_trace_seed42.json` / `..._evt001.json`, frozen with the engine's
`_kpi_snapshot()` shape (`cash`, `mrr`, `burn`, `runway`, ...) — see
`backend/tests/unit/engine/test_golden_trace.py`, which P1T004/P1T005 mirror.
The API-facing KPI shape (persisted in `TickLog.kpis`, streamed over WS) is
`kpi_snapshot()` from `app/engine/metrics.py`: `cash_balance`, `burn_rate`,
`runway_months`, `revenue`, `mrr`, `arr`, `customers`, `churn_rate`, `cac`,
`ltv`, `ltv_cac_ratio`, `new_customers`, `churned_customers`, `net_income`,
`costs` (asserted in P1T007 and P2T005/P3T002).

## C.3 Format B hurdle (mock provider output — deterministic)

`_mock_hurdle()` in `app/agents/llm/base.py` produces, for any prompt
containing `"Generate one context-aware hurdle"`:

```json
{
  "event_id": "evt_XXXXX", "trigger_timing": "Month N", "category": "<one of market|operational|financial|black_swan|internal>",
  "narrative": { "title": "...", "story": "...", "source_actor": "...", "believability_score": 0.6..0.99 },
  "mechanical_impact": {
    "immediate": {
      "cac_delta_percent": -5..35, "churn_delta_percent": 0..20,
      "new_signups_delta_percent": -40..0, "team_morale_delta": -0.20..0,
      "cash_burn_delta_monthly": 0..8000, "mrr_delta_percent": -10..0
    },
    "cascading": { "month 2": "Impact persists for the quarter." }
  },
  "ai_game_master_note": "Respond decisively — the market is watching."
}
```

Assertions on mock output are **shape** assertions (keys present, numbers in
range) — never exact values except for pinned `provider.register(...)` canned
responses used in unit tests.

## C.4 Format C report sections

- SURVIVAL METRICS: `survival_rate` (0..1), `median_lifespan_months`,
  `kill_vectors[].{cause,count,pct}`.
- WEAKNESSES: sorted `severity` ∈ {CRITICAL, HIGH, MEDIUM, LOW}.
- OPTIMIZATIONS: `tweak_key` ∈
  {churn, cac, price, fixed_monthly, starting_capital, client_concentration},
  `impact_on_survival_rate` in percentage points (may be negative).
- COUNTER-FACTUAL: `text` + `deltas[]`.

## C.5 Monte Carlo fixtures

| Input | Value |
|---|---|
| `n_runs` (qa) | 100 |
| `months` | 24 |
| `base_seed` | 42 |
| Hurdle template pool | `HURDLE_TEMPLATES` in `app/workers/monte_carlo.py` (10 entries, 5 categories × 2) |
| Auto-decision policy | highest `probability_success`, tie-break lowest `option_id` (`_auto_option`) |
| Determinism | same `(payload, base_seed, n_runs, months)` ⇒ identical `MonteCarloResult` |

## C.6 Stripe / webhook fixtures

| Fixture | Value |
|---|---|
| Event `customer.subscription.created` | `{"id":"evt_1","type":"customer.subscription.created","data":{"object":{"id":"sub_1","customer":"cus_1","status":"active","current_period_end":1893456000,"items":{"data":[{"price":{"id":"price_pro"}}]}}}}` |
| Event `customer.subscription.updated` | same shape, `type` swapped |
| Unknown event | `{"id":"evt_9","type":"invoice.payment_succeeded",...}` → `{"received":"invoice.payment_succeeded"}` |
| Bad signature | any payload + `Stripe-Signature: bad` → **400** |
| Duplicate delivery | resend event `evt_1` → `{"duplicate": true}` (idempotency) |

## C.7 API key fixture

| Field | Value |
|---|---|
| `name` | `qa-key` |
| `scopes` | `["simulations:read","simulations:write"]` |
| `rate_limit_rpm` | `10` |
| Wire format | `X-API-Key: <plaintext key>` (returned once at creation, stored hashed) |
| Prefix | first 12 chars of the plaintext key |

## C.8 Time / latency fixtures

- Engine: `run_simulation(state, 24, seed=42)` completes in **< 100 ms** (Checkpoint B).
- `optimization_service.measure_all_tweaks(payload, n_runs=20, seed=42)` — 6 tweaks × 20 runs,
  completes in **< 5 s** (default qa budget; tune via `OPT_TWEAK_RUNS`).
- API: p95 latency < 200 ms for all `/api/v1` handlers in Phase 4 (mock LLM, seeded DB).

## C.9 Deterministic seed constants

| Constant | Value | Purpose |
|---|---|---|
| `SEED_BASELINE` | `42` | P1T005 golden trace, P2T005, P3T004 |
| `SEED_STRESS` | `1337` | P2T006, P3T006 |
| `SEED_MC` | `2024` | P3T005, P4T005 |
| `SEED_GHOST` | `777` | P3T009 |

## C.10 Frontend mock data

- `features/marketing/__tests__/LandingPage.test.tsx` — marketing copy render.
- `features/settings/__tests__/SecurityPage.test.tsx` — password change form.
- `features/onboarding/__tests__/OnboardingWizard.test.tsx` — 3-step wizard.
- `components/charts/__tests__/ResilienceGauge.test.tsx` — score gauge.
- `stores/__tests__/notifications.test.ts` — notification store.
- `features/dashboard/__tests__/DashboardPage.test.tsx` — KPI cards + hooks.

All mock data for these tests lives inline in the test files (no network).
