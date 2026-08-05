# Project Progress — The Forge

Live status tracker for the build. Updated as phases complete; full detail in `tasks/todo.md` and per-phase cards in `tasks/phases/`.

**Last updated:** 2026-08-05

## Summary

| Phase | Scope | Status |
|---|---|---|
| 0 | Scaffolding & DevOps (T01–T05) | Complete |
| 1 | Auth & Multi-Tenancy (T06–T10) | Complete |
| 2 | Deterministic Simulation Engine (T11–T15) | Complete |
| 3 | Blueprints (T16–T19) | Complete |
| 4 | AI Cortex (T20–T24) | Complete |
| 5 | Simulation Runs (T25–T29) | **Complete** |
| 6 | Reports & Optimization (T30–T33) | Not started |
| 7 | App Shell, Dashboard & Marketing (T34–T39) | Not started |
| 8 | Monetization & Platform Features (T40–T46) | Not started |
| 9 | Production Hardening (T47–T51) | Not started |

**Next up:** Phase 6 — Reports & Optimization (T30–T33). Deps ready: Monte Carlo (T27), AI Cortex (T20–T24).

## Phase 5 — Simulation Runs (T25–T29) — Complete ✅

The deterministic engine is wired to the API: runs and tick logs are persisted, AI hurdles are injected with user decisions, Monte Carlo batches run through Celery, ticks stream over WebSocket, and the live Simulation Runner UI drives it all.

### Delivered

- **T25 — Run models + baseline service + API**
  - Models: `SimulationRun` (run_ id, workspace FK, mode, status, seed, config/result/state_snapshot JSONB), `TickLog` (unique run_id+month), `SimulationEvent` (Format B payload), `Decision` — Alembic migration `c7d2e8f1a3b4`
  - `app/engine/metrics.py` — shared KPI shape (cash_balance, burn_rate, runway_months, mrr, arr, customers, cac, ltv, ltv_cac_ratio…) + `resilience_score`
  - `app/services/simulation_service.py` — seeded deterministic baseline runner via `_run_trace`; `POST/GET /api/v1/simulations`, `GET /ticks`

- **T26 — Stress mode + decisions**
  - Deterministic per-seed hurdle schedule stored in `run.config["hurdle_months"]` (first randint(4,8), then every randint(3,6))
  - Segments advance the engine month-by-month, inject Hurdle Generator + Strategist hurdles (mock provider w/o key), park state in `state_snapshot`, set `awaiting_decision`
  - `POST /simulations/{id}/decide` — applies mechanical impact + chosen option's cash impact via `engine.events`, persists Decision, resumes to next hurdle; 409/422 guards

- **T27 — Monte Carlo worker**
  - `app/workers/monte_carlo.py` — Celery task `forge.monte_carlo`; LLM-free hot loop (10 deterministic templates across the 5 categories), auto-decision policy (highest success, tie-break lowest id), `aggregate_results` (survival_rate, p25/p50/p75, kill_vectors)
  - Redis progress key + pub/sub (best-effort, fakeredis in tests); control flag aborts to `cancelled`; `POST` returns 202 with `status: pending`, GET merges progress

- **T28 — WebSocket + controls**
  - `/ws/simulations/{id}` — token via query param (4401 invalid / 4403 no access), snapshot envelope + last-50-tick replay + Redis pub/sub forward
  - `POST /simulations/{id}/control` — pause/resume/cancel with strict transitions (else 409); status changes published over the channel

- **T29 — Simulation Runner UI**
  - `features/simulation/` — `api.ts` (typed TanStack Query hooks), `types.ts` (RunStatus, TickLog, HurdleEvent, WS envelope union), `RunnerPage` (status chip, control buttons, MC progress bar), `LiveFeed`, `SimulationListPage`
  - `stores/simulation.ts` Zustand store (tick dedupe by month), `lib/ws.ts` socket hook (exponential-backoff reconnect, max 5)
  - `components/charts/CashCurve.tsx` (Recharts, cash vs MRR + zero reference line), `features/warroom/HurdleCard` + `DecisionModal` (auto-opens on `awaiting_decision`)

### Verification (Checkpoint C → D bridge)

- `cd backend && pytest` → **238 passed** (incl. 36 new phase-5 tests)
- `cd backend && ruff check app tests && mypy app` → **clean**
- `alembic upgrade head` → clean through `c7d2e8f1a3b4` (simulation_runs, tick_logs, simulation_events, decisions)
- `cd frontend && npm run build && npm run lint` → build ok (Recharts added), lint 0 errors (1 pre-existing react-refresh warning)
- Full flow verified: baseline 201 + deterministic ticks → stress reaches `awaiting_decision` → decide advances → MC batch completes with `MonteCarloResult`; identical seeds → identical results

## Phase 4 — AI Cortex (T20–T24) — Complete ✅

The LLM layer on top of the deterministic engine. All LLM access flows through the provider abstraction + structured-output bridge; everything works with no API key via the deterministic `MockProvider`.

### Delivered

- **T20 — LLM provider abstraction** (`app/agents/llm/`) — `LLMResponse` dataclass, `LLMProvider` Protocol, deterministic `MockProvider` (sha256-seeded, substring registry), `OpenAICompatibleProvider` with retries + token-cost tracking, `get_llm_provider` factory (auto/mock).
- **T21 — Structured output bridge** (`app/agents/bridge.py`) — `generate_structured` with JSON extraction, `clamp_deltas`, repair-retry loop (max 2), raises `StructuredOutputError`.
- **T22 — Forge agent** (`forge.py` + `prompts/forge_system.md`) — blueprint review endpoint (200 + persists vulnerabilities, 404 cross-workspace, 502 invalid output).
- **T23 — Hurdle generator + chronicle** (`hurdle_generator.py`, `chronicle.py`) — `build_vital_signs` snapshot, Format B `HurdleEvent`, actor continuity.
- **T24 — Strategist** (`strategist.py`) — 2–4 options via bridge, pure-deterministic 12-month projections, `advise` alignment.

## How to run checks

```bash
cd backend
.venv/bin/python -m pytest          # full suite
.venv/bin/ruff check app tests      # lint
.venv/bin/mypy app                  # types
```

Full-stack (requires Docker): `docker compose up -d` then `curl localhost:8000/health`.
