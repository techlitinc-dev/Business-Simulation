# Task Checklist: The Forge — AI Business Simulation SaaS

Master index. **Detailed, self-contained task cards live in `tasks/phases/`** — each card has a description, acceptance criteria, verification commands, dependencies, exact files to create, and a scope size. Execute tasks in dependency order; sizes S/M are ideal for a single focused session.

Legend: **XS** = 1 file · **S** = 1–2 files · **M** = 3–5 files · **L** = 5–8 files

Verification conventions (defined in T01–T05):
- Backend tests: `cd backend && pytest`
- Backend lint: `cd backend && ruff check app tests && mypy app`
- Frontend build: `cd frontend && npm run build`
- Frontend lint: `cd frontend && npm run lint`
- Full stack: `docker compose up -d` then `curl localhost:8000/health`

---

## Phase 0 — Scaffolding & DevOps → `tasks/phases/phase-0.md`

- [ ] **T01** Monorepo skeleton, `.env.example`, Makefile, docker-compose (postgres, redis, backend, worker, frontend) — **M** — deps: none
- [ ] **T02** Backend scaffold: FastAPI app factory, pydantic-settings, structlog, `/health`, exception handlers — **M** — deps: T01
- [ ] **T03** Frontend scaffold: Vite+React+TS, Tailwind, shadcn/ui, router, dark theme AppShell — **M** — deps: T01
- [ ] **T04** Database layer: async SQLAlchemy session, base model, Alembic init + first migration — **M** — deps: T02
- [ ] **T05** CI: GitHub Actions workflow (backend lint+test, frontend lint+build) — **S** — deps: T02, T03

### Checkpoint A
- [ ] `docker compose up` boots all services; `GET /health` → 200; frontend renders AppShell; CI green on main

## Phase 1 — Auth & Multi-Tenancy → `tasks/phases/phase-1.md`

- [ ] **T06** User model + register/login/refresh JWT endpoints + password hashing — **M** — deps: T04
- [ ] **T07** Auth UI: login/register pages, token storage/refresh, protected routes, API client interceptors — **M** — deps: T06, T03
- [ ] **T08** Workspace/membership models + CRUD API + RBAC guard dependency — **M** — deps: T06
- [ ] **T09** Workspace UI: switcher, member list, invite accept flow — **M** — deps: T08, T07
- [ ] **T10** Email abstraction (verification + invite emails, SMTP/console fallback) — **S** — deps: T06

## Phase 2 — Deterministic Simulation Engine → `tasks/phases/phase-2.md`

- [ ] **T11** Engine state dataclasses + blueprint-payload→state compiler — **M** — deps: none (backend scaffold only: T02)
- [ ] **T12** Financial calculator: revenue, costs, cash flow, LTV/CAC, runway, MRR/ARR, NRR — **M** — deps: T11
- [ ] **T13** Monthly time-step loop + trigger checks (bankruptcy, profitability, funding need, milestones) — **M** — deps: T12
- [ ] **T14** Market dynamics: demand curve, price elasticity, seasonality, competitor pressure — **M** — deps: T12
- [ ] **T15** Event injector + golden-path engine tests (seeded 24-month trace, deterministic) — **M** — deps: T13, T14

### Checkpoint B
- [ ] Engine simulates 24 months from fixture blueprint in <100ms; identical seeds → identical traces; `pytest tests/unit/engine` green

## Phase 3 — Blueprints → `tasks/phases/phase-3.md`

- [x] **T16** Blueprint Pydantic schemas (Format A) + structural validation service — **M** — deps: T04, T11
- [x] **T17** Blueprint CRUD + versioning API — **M** — deps: T16, T08
- [x] **T18** Blueprint Builder UI: guided multi-step wizard + live validation panel — **L** — deps: T17, T07
- [x] **T19** Blueprint canvas view (React Flow visual model map) — **M** — deps: T17

## Phase 4 — AI Cortex → `tasks/phases/phase-4.md`

- [x] **T20** LLM provider abstraction: OpenAI-compatible client, env config, retry/timeout, token-cost tracking, mock provider — **M** — deps: T02
- [x] **T21** Structured output bridge: Pydantic schema validation + repair-retry loop — **M** — deps: T20
- [x] **T22** Forge agent + `POST /blueprints/{id}/review` (vulnerability analysis, Format A) — **M** — deps: T21, T17
- [x] **T23** Hurdle generator: vital-signs snapshot → Format B hurdle JSON + chronicle memory — **M** — deps: T21, T15
- [x] **T24** Strategist: 2–4 branching options + 12-month engine projection per option — **M** — deps: T23, T15

### Checkpoint C
- [x] With `LLM_*` env vars set, review + hurdle endpoints return schema-valid JSON; with no key, mock provider keeps dev flow working

## Phase 5 — Simulation Runs → `tasks/phases/phase-5.md`

- [x] **T25** SimulationRun/TickLog models + start/state API + baseline run service — **M** — deps: T15, T17
- [x] **T26** Stress-test mode: scheduled hurdle injection + `POST /simulations/{id}/decide` — **L** — deps: T25, T23, T24
- [x] **T27** Monte Carlo worker: Celery N-run batch, aggregation, Redis progress — **M** — deps: T26
- [x] **T28** WebSocket live tick/event streaming + run controls (pause/resume/cancel) — **M** — deps: T25
- [x] **T29** Simulation Runner UI: live cash curve, event feed, War Room decision modal — **L** — deps: T28, T26, T07

## Phase 6 — Reports & Optimization → `tasks/phases/phase-6.md`

- [x] **T30** Resilience audit generation: survival rate, median lifespan, kill vectors, ranked weaknesses — **M** — deps: T27
- [x] **T31** Counter-factual analysis + optimization recommendation service — **M** — deps: T30, T21
- [x] **T32** Report UI + Markdown/PDF export + shareable report links — **M** — deps: T30
- [x] **T33** Run/blueprint comparison endpoint + UI (V1 vs V2) — **M** — deps: T30

### Checkpoint D
- [x] End-to-end loop works: build blueprint → baseline run → stress test with decisions → Monte Carlo → resilience report → V1/V2 comparison

## Phase 7 — App Shell, Dashboard & Marketing → `tasks/phases/phase-7.md`

- [x] **T34** Design system polish: dark theme tokens, framer-motion transitions, skeletons, empty states — **M** — deps: T03
- [x] **T35** Main dashboard: KPI cards, resilience gauge, charts (Recharts), recent runs — **M** — deps: T25, T34
- [x] **T36** Onboarding wizard: industry / stage / primary fear — **S** — deps: T07
- [x] **T37** Notifications center + toast system — **S** — deps: T34
- [x] **T38** Settings pages: profile, workspace, members, security — **M** — deps: T09
- [x] **T39** Marketing landing page + pricing page — **M** — deps: T34

## Phase 8 — Monetization & Platform Features → `tasks/phases/phase-8.md`

- [ ] **T40** Stripe billing: plans, checkout, customer portal, idempotent webhook handler — **L** — deps: T08
- [ ] **T41** Usage metering + plan-limit enforcement + paywall/upgrade UI — **M** — deps: T40, T25
- [ ] **T42** Scenario marketplace: publish, browse/featured, clone — **M** — deps: T17
- [ ] **T43** Ghost Mode: autonomous AI personality runs + spectator UI — **L** — deps: T26, T24
- [ ] **T44** Public leaderboards + shareable report pages — **M** — deps: T30
- [ ] **T45** Enterprise API keys + per-key rate limiting — **M** — deps: T08
- [ ] **T46** Admin dashboard: users, workspaces, usage, revenue stats — **M** — deps: T40

## Phase 9 — Production Hardening → `tasks/phases/phase-9.md`

- [ ] **T47** Test coverage push: engine ≥90%, API integration ≥80% — **L** — deps: all core phases
- [ ] **T48** Observability: request-id logging, Sentry, Prometheus metrics, readiness probes — **M** — deps: T02
- [ ] **T49** Security hardening: global rate limits, CORS, security headers, audit log — **M** — deps: T45
- [ ] **T50** Seed data + demo blueprints/scenarios + docs (README, docs/api.md, docs/deployment.md, docs/llm-providers.md) — **M** — deps: T42
- [ ] **T51** Production deployment: prod Dockerfiles, docker-compose.prod.yml, DB backups, deploy runbook — **M** — deps: T48, T49

### Checkpoint E
- [ ] Staging deploy passes smoke tests; a new dev can run the full stack from README in <15 min; CI enforces lint+tests+coverage gates

---

## Progress Notes

_(Append dated entries here as tasks complete — keeps state across sessions/compaction.)_

- 2026-08-05: Phase 3 (T16–T19) complete. Backend: Format A Pydantic schemas (`app/schemas/blueprint.py`), structural validation service (`app/services/blueprint_service.py`, 5 rules + report DTOs), Blueprint/BlueprintVersion models with `bp_`/`bpv_` prefixed ids, Alembic migration `a1b2c3d4e5f6`, full CRUD/versioning/validate REST API under `/api/v1/blueprints` scoped by `X-Workspace-Id` header (new `get_current_workspace` dep). Frontend: Zustand draft store, 5-step BuilderWizard with debounced live validation panel, blueprint list/detail/edit pages, React Flow canvas view (`@xyflow/react@^12`) with pure `blueprintToFlow` layout. Verification: 152 backend tests pass (incl. 2 new unit + 1 new integration suites), ruff + mypy clean, alembic up/down/up clean, frontend build + lint pass (0 errors). Frontend unit tests skipped — no vitest runner scaffolded in T03 (build+lint are the gate per T18/T19).

- 2026-08-05: Phase 4 (T20–T24) complete. Backend AI Cortex: LLM provider abstraction (`app/agents/llm/base.py` — `LLMResponse`, `LLMProvider` Protocol, deterministic `MockProvider` with `sha256`-seeded output + substring registry; `openai_compat.py` — OpenAI-compatible client with exponential-backoff retries on timeout/rate-limit/connection/5xx, token-cost tracking; `factory.py` — auto/mock selection). Structured-output bridge (`app/agents/bridge.py` — `generate_structured` with JSON extraction, `clamp_deltas` on `MECHANICAL_DELTA_BOUNDS`, repair-retry loop max 2, raises `StructuredOutputError` in `app/core/exceptions.py`). Forge agent (`forge.py` + `prompts/forge_system.md`) with `POST /api/v1/blueprints/{id}/review` endpoint (200 + persists `identified_vulnerabilities` to `BlueprintVersion.vulnerabilities`, 404 cross-workspace, 502 on invalid LLM output). Hurdle generator (`hurdle_generator.py` + `prompts/hurdle_generation.md` — `build_vital_signs` snapshot, Format B `HurdleEvent` schema in `app/schemas/hurdle.py`, clamp=True). Chronicle narrative memory (`chronicle.py` — `ActorState`/`ChronicleEntry`/`Chronicle` with actor continuity + lossless `to_dict`/`from_dict`). Strategist (`strategist.py` + `prompts/strategic_options.md` — 2–4 options via bridge, pure-deterministic 12-month `project_option` reusing engine `tick`/`apply_event`, `advise` aligns options+projections). New `LLM_*` settings in `app/core/config.py` + `.env.example`. Verification: 202 backend tests pass (incl. 50 phase-4 unit/integration tests), ruff + mypy clean (fixed pre-existing mypy errors in `blueprint_service.py` + model column typing), no `openai` imports outside `openai_compat.py`, mock provider path verified end-to-end with no API key (factory → `MockProvider`, strategist REPL check with distinct projections, chronicle actor continuity across hurdle generations).

- 2026-08-05: Phase 5 (T25–T29) complete. Backend simulation runs: models (`app/models/simulation.py` — `SimulationRun`/`TickLog`/`SimulationEvent`/`Decision`, `RunStatus` enum single source of truth, Alembic migration `c7d2e8f1a3b4`), schemas (`app/schemas/simulation.py` — config, start request, `SimulationRunResponse`, `MonteCarloResult`, decision/control DTOs), `app/engine/metrics.py` (shared KPI shape + `resilience_score`). Service (`app/services/simulation_service.py`): baseline runner (seeded, deterministic), stress segments with deterministic per-seed hurdle schedules (`run.config["hurdle_months"]`), mock-provider hurdle+strategist injection, state parked in `state_snapshot` JSONB with lossless dataclass round-trip, `apply_decision` (409/422 guards), `control_run` pause/resume/cancel transitions, best-effort Redis progress/pub-sub publish. Monte Carlo worker (`app/workers/monte_carlo.py`): 10 deterministic in-process hurdle templates across the 5 spec categories, fixed auto-decision policy, `aggregate_results` (survival rate, p25/p50/p75 lifespan, kill vectors), Celery task with `_run_coro` eager-mode support. WebSocket (`app/api/v1/endpoints/ws.py` mounted at `/ws/simulations/{id}`, token auth via query param → 4401/4403, snapshot + 50-tick replay + pub/sub forward). Endpoints: `POST/GET /api/v1/simulations`, `GET /ticks`, `POST /decide`, `POST /control` (all workspace-scoped). MockProvider now falls back to deterministic valid hurdles/options so the no-key flow works end-to-end. Frontend: `features/simulation/{types,api,RunnerPage,LiveFeed,SimulationListPage}`, `features/warroom/{HurdleCard,DecisionModal}`, `components/charts/CashCurve` (Recharts), `stores/simulation.ts` Zustand store (dedupe by month), `lib/ws.ts` socket hook (exponential-backoff reconnect, max 5), router routes for list + runner. Recharts added to deps. Verification: 238 backend tests pass (36 new phase-5 tests), ruff + mypy clean, `alembic upgrade head` clean through the new tables, frontend `npm run build` + `npm run lint` pass (0 errors; 1 pre-existing react-refresh warning).

- 2026-08-05: Phase 6 (T30–T33) complete — Checkpoint D ✅. Backend reports: `Report` model (`app/models/report.py`, Alembic migration `e5f6a7b8c9d0`), `app/schemas/report.py` (SurvivalMetrics, Weakness, OptimizationEntry, PostMortemOutput, ComparisonResponse). `app/services/report_service.py`: `generate_resilience_audit` (deterministic SURVIVAL METRICS + ARCHITECTURAL WEAKNESSES markdown, idempotent persistence, 404/409 guards), `compare_runs` (delta math, ±1pp verdict, kill-vector changes sorted by |Δpp|). `app/services/optimization_service.py`: 6 fixed tweaks (churn/cac/price/fixed_monthly/starting_capital/client_concentration), `estimate_survival_delta` seeded-deterministic (`seed + tweak_index*1000 + run_index`), `measure_all_tweaks`. `app/agents/post_mortem.py` + `prompts/post_mortem.md`: bridge-validated AI narrative with engine-measured impact column, deterministic engine-only fallback, mock-provider canned output. `app/utils/pdf.py`: WeasyPrint + markdown → dark-styled PDF bytes. Endpoints: `GET /simulations/{run_id}/report`, `POST /report/export` (201 pdf_url, REPORT_STORAGE_DIR), `POST /report/share` + public `GET /reports/shared/{token}` (itsdangerous, 7-day, 410 expired / 404 tampered), `GET /reports/compare?a=&b=`, `GET /simulations` list. Frontend: `features/reports/` — `hooks.ts` (useReport/useSharedReport/useExportPdf/useShareReport/useCompare/useCompletedRuns), `ReportPage` (+shared `ReportView` with stat cards, weakness severity colors, optimization table), `SharedReportPage` (public route `/reports/shared/:token`), `ComparePage` (run pickers, delta badges, kill-vector table, verdict banner) + `/reports/compare` route; RunnerPage "View report" button. Added `weasyprint`, `markdown` (backend) and `react-markdown` (frontend). Verification: 274 backend tests pass (36 new phase-6 tests incl. PDF + export/share + compare), ruff + mypy clean, `alembic upgrade head` clean, frontend build + lint pass (0 errors), Checkpoint D end-to-end smoke: blueprint → MC → enriched report → compare works.
