# Phase 5 — Simulation Runs

Wire the deterministic engine to the API: persist runs and tick logs, inject AI hurdles with user decisions, batch Monte Carlo runs through Celery, stream ticks over WebSocket, and build the live Simulation Runner UI.

**Shared contracts used across this phase** (reference these exact shapes in every card):

- Run status enum (single source of truth, used in DB column, schemas, and frontend):
  `pending | running | awaiting_decision | paused | completed | dead | cancelled | failed`
  (`dead` = engine bankruptcy trigger fired; `completed` = survived all months.)
- Tick KPI shape stored in `TickLog.kpis` (JSONB) and streamed over WS — keys produced by `app/engine/metrics.py` (T15):
  ```json
  {"month": 7, "cash_balance": 218400.0, "burn_rate": 52000.0, "runway_months": 4.2,
   "revenue": 31500.0, "costs": 83500.0, "net_income": -52000.0, "mrr": 31500.0, "arr": 378000.0,
   "customers": 318, "churn_rate": 0.05, "cac": 850.0, "ltv": 2400.0, "ltv_cac_ratio": 2.82}
  ```
  Formulas (spec §5): `LTV = (ARPU × Gross Margin) / Monthly Churn Rate` · `Runway = Cash Balance / Monthly Burn Rate` · `CAC Payback = CAC / (ARPU × Gross Margin)`.
- Redis keys (created lazily, TTL 3600s): progress `sim:{run_id}:progress` → `{"completed": 40, "total": 100, "percent": 40}`; control flag `sim:{run_id}:control` → `"pause" | "cancel"`; pub/sub channel `sim:{run_id}:stream`.
- Redis access: add an async `redis.asyncio` client (from `settings.REDIS_URL`) exposed as a FastAPI dependency `get_redis()` in `app/api/deps.py`. All Redis usage must be **best-effort**: wrap publish/get in try/except so tests and dev run without Redis (tests override `get_redis` with `fakeredis.aioredis.FakeRedis` — add `fakeredis` to dev requirements in T28).
- Engine integration: use the pure engine API from T11–T15 (`compile_blueprint` in `app/engine/state.py`, monthly loop in `app/engine/loop.py`, event application in `app/engine/events.py`, KPI snapshot in `app/engine/metrics.py`). Adapt to the actual function names written in those tasks; never re-implement engine math in services. The engine stays pure — all DB/Redis/LLM I/O lives in services/workers.

---

## Task T25: Simulation run models + start/state API + baseline run service

**Description:** Create the persistence layer and synchronous baseline execution for simulation runs. Add SQLAlchemy 2.0 async models in `app/models/simulation.py`: `SimulationRun` (id via `new_id("run")` from `app/utils/ids.py`, `workspace_id` FK, `blueprint_version_id` FK, `mode` string enum, `status` default `"pending"`, `seed` Integer, `current_month` Integer default 0, `config` JSONB, `result` JSONB nullable, `state_snapshot` JSONB nullable — used by T26 to park engine state between requests, `started_at`/`finished_at`/`created_at` timestamps), `TickLog` (id uuid, `run_id` FK cascade-delete, `month` Integer, `kpis` JSONB, `UniqueConstraint(run_id, month)`), `SimulationEvent` (id via `new_id("evt")`, `run_id` FK, `month` Integer, `payload` JSONB = Format B hurdle, `status` string enum `pending | resolved | expired` default `"pending"`), and `Decision` (id via `new_id("dec")`, `run_id` FK, `event_id` FK, `option_id` String, `projection` JSONB nullable, `applied_at` timestamp). Generate an Alembic migration. Add Pydantic v2 schemas in `app/schemas/simulation.py`: `SimulationStartRequest {blueprint_version_id: str, mode: Literal["baseline"], seed: int | None = None, config: SimulationConfig = SimulationConfig()}` where `SimulationConfig {months: int = 24, difficulty: Literal["standard","hard","nightmare"] = "standard"}`; `SimulationRunResponse {id, workspace_id, blueprint_version_id, mode, status, seed, current_month, config, result, progress: dict | None, created_at, started_at, finished_at}`; `TickLogResponse {run_id, month, kpis}`. Build `app/services/simulation_service.py` with `start_baseline_run(db, workspace_id, req) -> SimulationRun`: load the `BlueprintVersion` (404 if not found or wrong workspace), generate a seed with `secrets.randbelow(2**31)` when `req.seed is None`, compile the blueprint payload to engine state via the T11 compiler, run the T13 monthly loop for `config.months` months (synchronous — a 24-month run completes in <100ms per Checkpoint B), persist one `TickLog` per month, and set `status` (`completed` or `dead`) and `result`:
```json
{"survived": true, "months_survived": 24, "final_cash": 812340.0, "final_mrr": 89000.0,
 "peak_cash": 812340.0, "min_cash": 140200.0, "resilience_score": 72}
```
(`resilience_score` comes from `app/engine/metrics.py`.) Add `app/api/v1/endpoints/simulations.py` and register it in `app/api/v1/router.py` under prefix `/simulations`: `POST /api/v1/simulations` → 201 `SimulationRunResponse` (requires auth + workspace membership via existing deps; runs synchronously and returns the finished run); `GET /api/v1/simulations/{id}` → 200 `SimulationRunResponse` (404 if not in caller's workspace; `progress` is `None` for non-Monte-Carlo runs); `GET /api/v1/simulations/{id}/ticks` → 200 `list[TickLogResponse]` ordered by month. All endpoints workspace-scoped through the existing `app/api/deps.py` guards.

**Acceptance criteria:**
- [ ] Alembic migration applies cleanly (`cd backend && alembic upgrade head`) and creates tables `simulation_runs`, `tick_logs`, `simulation_events`, `decisions`
- [ ] `POST /api/v1/simulations` with a valid `blueprint_version_id` returns 201 with `status` in `{completed, dead}`, `result.survived` set, and `seed` echoed (or generated when omitted)
- [ ] Same blueprint + same explicit `seed` on two POSTs produces identical `TickLog.kpis` for every month (determinism)
- [ ] `GET /api/v1/simulations/{id}/ticks` returns exactly `config.months` rows (or fewer if the run died early), ordered by month, each matching the shared KPI shape
- [ ] Requests for a run in another workspace return 404; unauthenticated requests return 401

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_simulation_service.py tests/integration/api/test_simulations.py -v` — create both files; integration tests build user+workspace+blueprint version via existing fixtures/helpers from Phases 1–3, reuse the T15 engine fixture blueprint payload (copy into `tests/fixtures/` if not already shared)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `curl -X POST localhost:8000/api/v1/simulations -H "Authorization: Bearer $TOKEN" -d '{"blueprint_version_id":"<id>","mode":"baseline","seed":42}'` returns 201 in under ~2s with 24 tick rows fetchable

**Dependencies:** T15, T17

**Files likely touched:**
- `backend/app/models/simulation.py`
- `backend/app/schemas/simulation.py`
- `backend/app/services/simulation_service.py`
- `backend/app/api/v1/endpoints/simulations.py`
- `backend/app/api/v1/router.py`
- `backend/alembic/versions/<new>_simulation_runs.py`
- `backend/tests/unit/services/test_simulation_service.py`
- `backend/tests/integration/api/test_simulations.py`

**Estimated scope:** M

---

## Task T26: Stress-test mode — scheduled hurdle injection + decision application

**Description:** Add interactive stress-test runs where the AI Cortex injects hurdles at realistic intervals and the run pauses for a user decision. Widen `SimulationStartRequest.mode` to `Literal["baseline","stress"]`. Stress runs execute the engine loop month-by-month inside `simulation_service.run_stress_segment(db, run) -> SimulationRun`, which: (1) reconstructs engine state from `run.state_snapshot` (or compiles fresh from the blueprint version on first segment); (2) advances months until the next scheduled hurdle month, run end, or bankruptcy, persisting `TickLog` rows; (3) at a hurdle month, builds the vital-signs snapshot (spec §6 Step 1) from current engine KPIs:
```json
{"burn_rate": 47000, "runway_months": 8, "cash_reserves": 376000, "cac": 850, "ltv": 2400,
 "revenue_concentration": {"top_client_percent": 40, "top_3_clients_percent": 72},
 "vp_sales_hired": false, "competitor_x_raised_series_b": true, "organic_acquisition": false}
```
(4) calls the Hurdle Generator agent (T23) **through `app/agents/bridge.py` and the `app/agents/llm/` provider abstraction only** — env-configured (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`), deterministic mock provider when no key — producing a Format B hurdle; (5) calls the Strategist (T24) to attach a 12-month engine projection per strategic option, stored in the event payload under `options_projection`; (6) persists a `SimulationEvent` (status `pending`) with the merged payload, serializes engine state into `run.state_snapshot`, sets `run.status = "awaiting_decision"`, and returns. Hurdle schedule must be deterministic per seed: with `rng = random.Random(run.seed)`, first hurdle at month `rng.randint(4, 8)`, subsequent hurdles every `rng.randint(3, 6)` months; store the schedule in `run.config["hurdle_months"]`. Format B hurdle payload (spec §10 — validate with a Pydantic schema `HurdleEvent` in `app/schemas/hurdle.py`):
```json
{"event_id": "evt_001", "trigger_timing": "Month 7, Week 2", "category": "market",
 "narrative": {"title": "...", "story": "...", "source_actor": "Competitor X", "believability_score": 0.92},
 "mechanical_impact": {"immediate": {"cac_delta_percent": 35, "churn_delta_percent": 15,
   "new_signups_delta_percent": -40, "team_morale_delta": -0.10, "cash_burn_delta_monthly": 0},
  "cascading": {"month_2": "...", "month_3": "..."}},
 "strategic_options": [{"option_id": "A", "name": "...", "description": "...",
   "cash_impact_monthly": -8000, "probability_success": 0.45,
   "second_order_risk": "...", "required_execution": "..."}],
 "ai_game_master_note": "..."}
```
`category` must be one of `market | operational | financial | black_swan | internal` (spec §6 hurdle categories). Build `app/services/decision_service.py` with `apply_decision(db, workspace_id, run_id, req) -> Decision` and expose it in `app/api/v1/endpoints/decisions.py` as `POST /api/v1/simulations/{id}/decide` with body `DecisionRequest {event_id: str, option_id: str}` (`app/schemas/decision.py`) → 200 `DecisionAppliedResponse {decision_id, event_id, option_id, run: SimulationRunResponse}`. The service must: verify run status is `awaiting_decision` and the event is `pending` (409 otherwise); verify `option_id` exists in the event's `strategic_options` (404/422 otherwise); apply the hurdle's `mechanical_impact.immediate` deltas **and** the chosen option's `cash_impact_monthly` to the deserialized engine state via `app/engine/events.py` (engine clamps impossible deltas — the AI never writes state directly); persist a `Decision` row (`projection` = the option's entry from `options_projection`); mark the event `resolved`; then immediately resume `run_stress_segment` to the next hurdle/end so the response contains fresh ticks and the new status. New runs of mode `stress` execute their first segment synchronously inside `POST /api/v1/simulations` (still 201).

**Acceptance criteria:**
- [ ] `POST /api/v1/simulations` with `mode:"stress"` and no LLM key (mock provider) returns 201 and eventually reaches `awaiting_decision` with a `SimulationEvent` whose payload validates against `HurdleEvent` (category in the 5 allowed values, 2–4 strategic options)
- [ ] Two stress runs with the same blueprint + seed produce identical hurdle months and identical mock hurdle payloads
- [ ] `POST /simulations/{id}/decide` with a valid `event_id`/`option_id` returns 200, persists a `Decision`, marks the event `resolved`, and the response run shows `current_month` advanced and `status` in `{awaiting_decision, completed, dead}`
- [ ] `decide` on a run not in `awaiting_decision` (or with an unknown `option_id`) returns 409 (or 422) and changes nothing
- [ ] The chosen option's `cash_impact_monthly` is visible in subsequent tick KPIs (e.g. costs shift by that amount)
- [ ] With `LLM_*` env vars unset, the full flow works end-to-end via the deterministic mock provider; no provider name is hardcoded anywhere

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_decision_service.py tests/unit/services/test_simulation_service.py tests/integration/api/test_decisions.py -v` — create `test_decision_service.py` and `test_decisions.py`, extend `test_simulation_service.py`; tests force the mock provider (monkeypatch settings to clear `LLM_API_KEY`) and seed every run
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: with no `LLM_API_KEY`, start a stress run, `GET /simulations/{id}` until `awaiting_decision`, POST a decision, and observe `current_month` advance and a new tick row

**Dependencies:** T25, T23, T24

**Files likely touched:**
- `backend/app/schemas/simulation.py` (widen `mode`)
- `backend/app/schemas/hurdle.py`
- `backend/app/schemas/decision.py`
- `backend/app/services/simulation_service.py`
- `backend/app/services/hurdle_service.py`
- `backend/app/services/decision_service.py`
- `backend/app/api/v1/endpoints/simulations.py`
- `backend/app/api/v1/endpoints/decisions.py`
- `backend/app/api/v1/router.py`
- `backend/tests/unit/services/test_decision_service.py`
- `backend/tests/integration/api/test_decisions.py`

**Estimated scope:** L

---

## Task T27: Monte Carlo worker (Celery) — N-run batch, aggregation, Redis progress

**Description:** Add batch Monte Carlo simulation as a Celery background job. Widen `SimulationStartRequest.mode` to `Literal["baseline","stress","monte_carlo"]` and add `n_runs: int = 100` (ge=1, le=1000) to `SimulationConfig` (default from Format A `simulation_parameters.monte_carlo_runs`). Create `app/workers/celery_app.py` if absent (broker/backend = `settings.REDIS_URL`, JSON serializer) and `app/workers/monte_carlo.py` with task `run_monte_carlo(run_id: str)`. Monte Carlo runs **must not call the LLM in the hot loop** (100 runs × 50 calls is too slow/expensive — spec §14): instead define a deterministic in-process hurdle template pool in `monte_carlo.py` — 8–10 templates spanning the 5 spec §6 categories (`market`, `operational`, `financial`, `black_swan`, `internal`), each holding only `mechanical_impact.immediate`-style deltas plus 2 generic options with `probability_success` — and sample them with `rng = random.Random(run.seed + i)` for run `i` (hurdle months sampled the same way as T26). Decisions are auto-applied with a fixed policy: pick the option with the highest `probability_success`, tie-break by lowest `option_id`. Each sub-run compiles the blueprint via the T11 compiler, executes the T13 loop for `config.months`, and records `{seed, survived, lifespan_months, kill_vector}` where `kill_vector` is the category of the hurdle active when the run died, or `"natural_causes"` if cash went negative with no active hurdle. Extract a pure function `aggregate_results(outcomes: list[dict]) -> MonteCarloResult` (Pydantic model in `app/schemas/simulation.py`):
```json
{"n_runs": 100, "survival_rate": 0.34, "median_lifespan_months": 11, "p25_lifespan_months": 7,
 "p75_lifespan_months": 18, "kill_vectors": {"financial": 30, "market": 22, "natural_causes": 14},
 "runs_summary": [{"seed": 1042, "survived": false, "lifespan_months": 9}]}
```
(`kill_vectors` counts only failed runs, keyed by category — this feeds the Format C report in T30.) After each sub-run, write progress to Redis key `sim:{run_id}:progress` and publish a `{"type":"progress",...}` envelope to channel `sim:{run_id}:stream` (both best-effort per the shared contract); between sub-runs check `sim:{run_id}:control == "cancel"` and abort with status `cancelled` if set (T28 relies on this). On completion set `run.status = completed`, `run.result = aggregate_results(...)`, `finished_at`; on exception set status `failed` and `result.error`. Update `POST /api/v1/simulations`: for `monte_carlo` mode create the run with status `pending`, enqueue `run_monte_carlo.delay(run_id)`, return **202** with `SimulationRunResponse`. Update `GET /api/v1/simulations/{id}` to merge the Redis progress key into `progress` for Monte Carlo runs. Tests configure Celery with `task_always_eager=True` and override `get_redis`/worker Redis with `fakeredis`.

**Acceptance criteria:**
- [ ] `POST /api/v1/simulations` with `mode:"monte_carlo"`, `config.n_runs:20` returns 202 with `status:"pending"`, and (with eager Celery) a following `GET /simulations/{id}` shows `status:"completed"` and a result matching the `MonteCarloResult` shape
- [ ] Same blueprint + seed + n_runs yields byte-identical `result` (determinism); different seeds change outcomes
- [ ] `result.survival_rate` ∈ [0,1], `median_lifespan_months` ≤ `config.months`, `sum(kill_vectors.values()) == n_runs - survived_count`
- [ ] Setting Redis `sim:{id}:control = "cancel"` mid-batch stops the task and leaves the run `cancelled` (test with eager mode + monkeypatched redis)
- [ ] No LLM provider call occurs during Monte Carlo execution (assert via mock provider call counter in tests)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_monte_carlo.py tests/integration/api/test_monte_carlo_api.py -v` — create both; unit tests cover `aggregate_results` edge cases (all survive, all die at month 0, n_runs=1) with synthetic outcomes; integration test runs a 10-run batch eagerly
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `docker compose up -d` (worker service from T01), POST a 50-run Monte Carlo, watch `redis-cli GET sim:{id}:progress` climb to 100%

**Dependencies:** T26

**Files likely touched:**
- `backend/app/workers/celery_app.py`
- `backend/app/workers/monte_carlo.py`
- `backend/app/schemas/simulation.py`
- `backend/app/services/simulation_service.py`
- `backend/app/api/v1/endpoints/simulations.py`
- `backend/tests/unit/services/test_monte_carlo.py`
- `backend/tests/integration/api/test_monte_carlo_api.py`

**Estimated scope:** M

---

## Task T28: WebSocket live tick streaming + run controls

**Description:** Stream live simulation output to the browser and let users control runs. Add `get_redis()` to `app/api/deps.py` (module-level `redis.asyncio.from_url(settings.REDIS_URL, decode_responses=True)`; overridable in tests with `fakeredis.aioredis.FakeRedis` — add `fakeredis` to dev requirements). Add a publish helper in `app/services/simulation_service.py` (e.g. `async publish_envelope(redis, run_id, type, data)`) that publishes JSON to channel `sim:{run_id}:stream`, best-effort (try/except, never breaks a run without Redis). Wire it into T25/T26/T27 paths: after each persisted `TickLog` publish `{"type":"tick","data":{"month":7,"kpis":{...}}}`; after each `SimulationEvent` publish `{"type":"event","data":<event payload>}`; on every status change publish `{"type":"status","data":{"status":"awaiting_decision"}}`. Create `app/api/v1/endpoints/ws.py` with route `WS /ws/simulations/{id}` (mounted on the app in `app/main.py`, **not** under the `/api/v1` prefix). Auth: browsers cannot set headers on WebSocket, so accept `?token=<access_token>`, verify with the existing JWT decode in `app/core/security.py`, then load the run and check workspace membership; on failure close with code `4401` (bad/expired token) or `4403` (no access). On connect: send `{"type":"snapshot","data":<SimulationRunResponse>}` followed by the last 50 persisted ticks as `tick` envelopes (replay), then subscribe to `sim:{run_id}:stream` with `redis.asyncio` pub/sub and forward every message until disconnect; handle client `ping` with `pong`; close cleanly on run terminal status. Add run controls to `app/api/v1/endpoints/simulations.py`: `POST /api/v1/simulations/{id}/control` with body `ControlRequest {action: Literal["pause","resume","cancel"]}` (`app/schemas/simulation.py`) → 200 `SimulationRunResponse`. Transitions (else 409): `pause`: `running|awaiting_decision` → `paused`; `resume`: `paused` → `awaiting_decision` if a `pending` SimulationEvent exists else `running`; `cancel`: any non-terminal status → `cancelled` and set Redis `sim:{run_id}:control="cancel"` so the Monte Carlo worker aborts. `pause`/`resume` also set/clear the Redis flag for future async runners. Publish a `status` envelope on each transition.

**Acceptance criteria:**
- [ ] Connecting to `/ws/simulations/{id}` with a valid token receives a `snapshot` message first, then replayed `tick` messages for existing ticks
- [ ] Starting a stress run and reaching a hurdle while connected delivers an `event` envelope and a `status` envelope with `awaiting_decision` without polling
- [ ] Connecting with an invalid token closes with code 4401; a run from another workspace closes with 4403
- [ ] `POST /simulations/{id}/control {"action":"pause"}` on an `awaiting_decision` run returns 200 with `status:"paused"`; `resume` returns it to `awaiting_decision`; `cancel` returns `cancelled` and a second `cancel` returns 409
- [ ] All tests pass without a real Redis server (fakeredis override)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/api/test_ws.py tests/integration/api/test_control.py -v` — create both; use `starlette.testclient.TestClient.websocket_connect` with dependency-overridden fakeredis; test snapshot, replay, pub/sub forward (publish via the fake redis from the test), and auth close codes
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `docker compose up -d`, then `wscat -c "ws://localhost:8000/ws/simulations/<id>?token=<jwt>"` shows the snapshot envelope and live ticks while a run executes

**Dependencies:** T25

**Files likely touched:**
- `backend/app/api/deps.py`
- `backend/app/api/v1/endpoints/ws.py`
- `backend/app/api/v1/endpoints/simulations.py`
- `backend/app/services/simulation_service.py`
- `backend/app/schemas/simulation.py`
- `backend/app/main.py`
- `backend/requirements.txt` (fakeredis dev dep)
- `backend/tests/integration/api/test_ws.py`
- `backend/tests/integration/api/test_control.py`

**Estimated scope:** M

---

## Task T29: Simulation Runner UI — live cash curve, event feed, War Room decision modal

**Description:** Build the interactive run page (spec §9 Phase 3–4). Route: add `/workspaces/:workspaceId/simulations/:runId` to `src/router.tsx`, rendering `src/features/simulation/RunnerPage.tsx`. Create `src/features/simulation/api.ts` with typed functions over the existing `src/lib/api-client.ts` wrapper: `startSimulation(workspaceId, body)`, `getSimulation(runId)`, `getTicks(runId)`, `decide(runId, body)`, `control(runId, action)` — plus shared TS types in `src/features/simulation/types.ts` mirroring the backend contracts (`RunStatus` union, `SimulationRun`, `TickLog`, `HurdleEvent` with `strategic_options` and `options_projection`, WS envelope union). State: extend (or create) `src/stores/simulation.ts` (Zustand) with `{run, ticks: TickLog[], events: HurdleEvent[], liveStatus, hydrate(run, ticks), appendTick(t), appendEvent(e), setStatus(s)}`. Live data: create `src/lib/ws.ts` exporting `useSimulationSocket(runId)` — opens `ws(s)://<api-host>/ws/simulations/{id}?token=<access token from auth store>`, dispatches envelopes into the Zustand store (`snapshot`→hydrate meta, `tick`→appendTick, `event`→appendEvent, `status`→setStatus, `progress`→store), auto-reconnects with exponential backoff (max 5 tries), exposes `connectionStatus: "connecting"|"open"|"closed"`. UI on `RunnerPage`: header with run mode, status chip (color-coded: `awaiting_decision` = amber pulsing, `dead` = red, `completed` = green) and control buttons (Pause / Resume / Cancel → `control()` with TanStack Query mutation, disabled per status); main grid: `src/components/charts/CashCurve.tsx` (2/3 width) — Recharts `LineChart` with `cash_balance` (primary line) and `mrr` (secondary, dashed) over `month`, dark theme tokens, `isAnimationActive` for the live-draw effect, runway reference line at cash=0; `src/features/simulation/LiveFeed.tsx` (1/3) — reverse-chronological feed of events (hurdle titles, styled cards) interleaved with milestone ticks (bankruptcy, profitability), auto-scrolling. Initial load fetches `getSimulation` + `getTicks` via TanStack Query to hydrate the store before the socket takes over. War Room (spec §8): when `liveStatus === "awaiting_decision"` and an unresolved event exists, open `src/features/warroom/DecisionModal.tsx` (shadcn `Dialog`, non-dismissable): renders `src/features/warroom/HurdleCard.tsx` (narrative title, story, source actor, category badge, immediate mechanical impacts as signed delta chips) and the 2–4 strategic options side-by-side (`grid grid-cols-1 md:grid-cols-2`), each card showing name, description, `cash_impact_monthly` (colored +/-), `probability_success` as a progress bar, `second_order_risk`, and a mini Recharts 12-month projection line from `options_projection[option_id]` when present; selecting a card highlights it, Confirm fires `decide()` mutation, on success closes the modal and the feed shows the applied decision. All styling follows the existing dark theme + shadcn/ui primitives from T03; loading skeleton while hydrating; empty-state copy when a run has no ticks yet.

**Acceptance criteria:**
- [ ] Navigating to the Runner page for a finished run renders the full cash curve from `GET /ticks` without a socket connection
- [ ] During a live stress run, new ticks animate onto the chart and hurdle cards appear in the feed via WS only (no polling)
- [ ] When the run reaches `awaiting_decision`, the War Room modal opens automatically, lists 2–4 options with cash impact and success probability, and Confirm POSTs `{event_id, option_id}` then closes and resumes the stream
- [ ] Pause/Resume/Cancel buttons reflect and drive run status; terminal runs disable all controls
- [ ] Socket disconnect shows a "reconnecting" indicator and recovers without duplicate ticks (dedupe by `month` in `appendTick`)

**Verification:**
- [ ] Tests pass: `cd frontend && npm run build` (no test runner is configured for the frontend; type-checking via the Vite/TS build is the gate)
- [ ] Lint/build passes: `cd frontend && npm run lint && npm run build`
- [ ] Manual check: with backend + worker up, start a stress run from the UI, watch the cash curve draw live, decide in the War Room modal when it opens, and see the curve continue; then start a Monte Carlo run and watch the progress bar advance

**Dependencies:** T28, T26, T07

**Files likely touched:**
- `frontend/src/features/simulation/RunnerPage.tsx`
- `frontend/src/features/simulation/LiveFeed.tsx`
- `frontend/src/features/simulation/api.ts`
- `frontend/src/features/simulation/types.ts`
- `frontend/src/features/warroom/HurdleCard.tsx`
- `frontend/src/features/warroom/DecisionModal.tsx`
- `frontend/src/components/charts/CashCurve.tsx`
- `frontend/src/stores/simulation.ts`
- `frontend/src/lib/ws.ts`
- `frontend/src/router.tsx`

**Estimated scope:** L
