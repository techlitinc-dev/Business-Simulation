# Implementation Plan: The Forge — AI-Powered Business Simulation SaaS

## Overview

"The Forge" is a production-ready SaaS that acts as a **digital wind tunnel for entrepreneurs**: users build a business blueprint, simulate 24+ months of operations on a deterministic financial engine, get stress-tested by LLM-generated context-aware hurdles, make branching strategic decisions in a "War Room", and receive Monte-Carlo-driven resilience audits with prescriptive optimizations.

The system has two brains (per `Business_Simulation_System_Plan.md`):
- **Deterministic Engine** (pure Python): cash, payroll, churn, demand, LTV/CAC — physics that cannot be overridden.
- **AI Cortex** (cheap LLM, e.g. DeepSeek via OpenAI-compatible API): narrative hurdles, strategic options, post-mortems — meaning layered on top of the engine's math.

On top of the core simulation product, this plan adds the SaaS layer that makes it commercially viable: auth, multi-tenant workspaces, Stripe billing with usage metering, a scenario marketplace, Ghost Mode, leaderboards, an enterprise API, and an admin dashboard.

**Target reader:** every task card in `tasks/phases/` is written so a cheap LLM (or junior dev) can execute it in isolation — explicit file paths, acceptance criteria, and verification commands are given for each.

## Architecture Decisions

- **Monorepo** with `backend/` (FastAPI) and `frontend/` (React) — one repo, one docker-compose, simplest deploy story.
- **Backend: Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Alembic + Pydantic v2.** PostgreSQL for relational data; Redis for cache, Celery broker, and live-run state.
- **Frontend: React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui + Recharts + React Flow + TanStack Query + Zustand.** Dark-first "war room" aesthetic.
- **LLM access through a provider abstraction** (`app/agents/llm/`) using the OpenAI-compatible SDK. Provider, model, base URL, and key come from env vars (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`), so any cheap model (DeepSeek, GPT-4o-mini, Claude Haiku, local vLLM/Ollama) plugs in with zero code changes.
- **Structured output bridge:** every LLM response is validated against a Pydantic schema; invalid output triggers an automatic repair-retry loop (max 2 retries) before failing gracefully. The AI never writes engine state directly — it emits JSON deltas that the engine validates and applies.
- **Deterministic engine is LLM-free and pure:** `app/engine/` has no I/O, no DB, no network — only dataclasses in, dataclasses out. This makes it fast (100 Monte Carlo runs in seconds) and trivially unit-testable.
- **Monte Carlo runs are Celery background jobs** with progress published to Redis and streamed to the client over WebSocket.
- **Auth:** JWT access + refresh tokens, hashed passwords (argon2/bcrypt via passlib), workspace-scoped RBAC (owner/admin/member).
- **Billing:** Stripe Checkout + Customer Portal + webhooks; plan limits enforced server-side via a usage-metering service (runs/month, Monte Carlo size, seats).
- **Time-series KPI logs** are stored as JSONB rows per tick in PostgreSQL (simple, sufficient at this scale) instead of introducing InfluxDB — see Open Questions.

## Folder Structure

```
Business-Simulation/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app factory, middleware, routers
│   │   ├── core/
│   │   │   ├── config.py               # pydantic-settings, env-driven
│   │   │   ├── security.py             # JWT, password hashing
│   │   │   ├── logging.py              # structlog setup
│   │   │   ├── exceptions.py           # domain exceptions + handlers
│   │   │   └── rate_limit.py           # slowapi limiter
│   │   ├── db/
│   │   │   ├── base.py                 # DeclarativeBase, common columns
│   │   │   └── session.py              # async engine + session factory
│   │   ├── models/                     # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── workspace.py            # workspace, membership, invite
│   │   │   ├── blueprint.py            # blueprint + version
│   │   │   ├── simulation.py           # run, tick_log, event, decision
│   │   │   ├── report.py
│   │   │   ├── scenario.py             # marketplace scenarios
│   │   │   ├── billing.py              # subscription, usage_record
│   │   │   └── api_key.py
│   │   ├── schemas/                    # Pydantic v2 request/response DTOs
│   │   │   ├── auth.py  user.py  workspace.py  blueprint.py
│   │   │   ├── simulation.py  hurdle.py  decision.py  report.py
│   │   │   ├── billing.py  scenario.py  admin.py  common.py
│   │   ├── api/
│   │   │   ├── deps.py                 # get_db, current_user, workspace guard
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   │           ├── auth.py  users.py  workspaces.py
│   │   │           ├── blueprints.py  simulations.py  decisions.py
│   │   │           ├── reports.py  scenarios.py  billing.py
│   │   │           ├── api_keys.py  admin.py  webhooks.py  ws.py
│   │   ├── services/                   # business logic (one module per domain)
│   │   │   ├── auth_service.py  workspace_service.py
│   │   │   ├── blueprint_service.py  simulation_service.py
│   │   │   ├── hurdle_service.py  decision_service.py
│   │   │   ├── report_service.py  optimization_service.py
│   │   │   ├── billing_service.py  metering_service.py
│   │   │   ├── scenario_service.py  ghost_service.py
│   │   │   ├── notification_service.py  admin_service.py
│   │   ├── engine/                     # DETERMINISTIC CORE — no I/O, no LLM
│   │   │   ├── state.py                # BusinessState, FinancialState, MarketState
│   │   │   ├── financials.py           # revenue/cost/cash-flow/LTV/CAC/runway math
│   │   │   ├── market.py               # demand curve, elasticity, seasonality
│   │   │   ├── loop.py                 # time-step loop, trigger checks
│   │   │   ├── events.py               # event/hurdle application to state
│   │   │   └── metrics.py              # KPI snapshots, resilience score
│   │   ├── agents/                     # AI CORTEX
│   │   │   ├── llm/
│   │   │   │   ├── base.py             # LLMProvider protocol, LLMResponse, cost tracking
│   │   │   │   ├── openai_compat.py    # OpenAI SDK client (DeepSeek/any compatible)
│   │   │   │   └── factory.py          # build provider from settings
│   │   │   ├── prompts/
│   │   │   │   ├── forge_system.md     # system prompt from plan doc §13
│   │   │   │   ├── hurdle_generation.md
│   │   │   │   ├── strategic_options.md
│   │   │   │   ├── post_mortem.md
│   │   │   │   └── ghost_personality.md
│   │   │   ├── forge.py                # blueprint review, vulnerabilities
│   │   │   ├── hurdle_generator.py
│   │   │   ├── strategist.py           # branching options + outcome projection
│   │   │   ├── post_mortem.py          # resilience audit narrative
│   │   │   ├── ghost.py                # autonomous personalities
│   │   │   ├── chronicle.py            # narrative memory / actor continuity
│   │   │   └── bridge.py               # JSON schema validation + repair loop
│   │   ├── workers/
│   │   │   ├── celery_app.py
│   │   │   ├── monte_carlo.py          # batch simulation runs
│   │   │   └── email_tasks.py
│   │   └── utils/
│   │       ├── ids.py                  # prefixed ids (bp_, run_, evt_)
│   │       ├── pdf.py                  # report PDF rendering (weasyprint)
│   │       └── email.py                # email sender abstraction + console fallback
│   ├── alembic/                        # migrations
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/        engine/  services/  agents/
│   │   ├── integration/ api/
│   │   └── fixtures/
│   ├── requirements.txt
│   ├── pyproject.toml                  # ruff, mypy, pytest config
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.tsx  App.tsx  router.tsx
│   │   ├── lib/
│   │   │   ├── api-client.ts           # fetch wrapper, auth interceptors
│   │   │   ├── ws.ts                   # WebSocket hook for live ticks
│   │   │   ├── utils.ts  constants.ts
│   │   ├── stores/                     # Zustand: auth, workspace, simulation
│   │   ├── components/
│   │   │   ├── ui/                     # shadcn/ui primitives
│   │   │   ├── layout/                 # AppShell, Sidebar, Topbar
│   │   │   └── charts/                 # CashCurve, BurnChart, ResilienceGauge...
│   │   ├── features/
│   │   │   ├── auth/                   # LoginPage, RegisterPage, hooks
│   │   │   ├── onboarding/             # industry/stage/fear wizard
│   │   │   ├── dashboard/              # KPI cards, recent runs
│   │   │   ├── blueprint/              # BuilderWizard, CanvasView, validation panel
│   │   │   ├── simulation/             # RunnerPage, LiveFeed, tick stream
│   │   │   ├── warroom/                # HurdleCard, DecisionModal, option comparison
│   │   │   ├── reports/                # ReportPage, export, comparison view
│   │   │   ├── marketplace/            # browse/publish/clone scenarios
│   │   │   ├── ghost/                  # Ghost Mode setup + spectator view
│   │   │   ├── leaderboard/
│   │   │   ├── billing/                # PricingPage, checkout, usage meters
│   │   │   ├── settings/               # profile, workspace, members, API keys
│   │   │   └── marketing/              # LandingPage
│   │   └── styles/                     # tailwind, theme tokens
│   ├── package.json  vite.config.ts  tailwind.config.ts  tsconfig.json
│   └── Dockerfile
├── docker-compose.yml                  # postgres, redis, backend, worker, frontend
├── docker-compose.prod.yml
├── .github/workflows/ci.yml
├── Makefile                            # dev, test, lint, migrate, seed
├── .env.example
├── docs/
│   ├── api.md  architecture.md  deployment.md  llm-providers.md
└── tasks/
    ├── plan.md                         # this file
    ├── todo.md                         # master checklist
    └── phases/                         # detailed task cards (one file per phase)
```

## Data Model (summary)

| Entity | Key fields | Notes |
|---|---|---|
| User | id, email, pw_hash, name, is_verified, is_admin | |
| Workspace | id, name, slug, plan_tier, stripe_customer_id | multi-tenant boundary |
| Membership | user_id, workspace_id, role(owner/admin/member) | |
| Invite | token, email, workspace_id, expires_at | |
| Blueprint | id, workspace_id, name, current_version, industry, stage | |
| BlueprintVersion | id, blueprint_id, version, payload(JSONB), vulnerabilities(JSONB) | payload = Format A from plan doc |
| SimulationRun | id, blueprint_version_id, mode(baseline/stress/monte_carlo/ghost), status, seed, config(JSONB), result(JSONB) | |
| TickLog | run_id, month, kpis(JSONB) | time-series |
| SimulationEvent | run_id, month, payload(JSONB = Format B hurdle), status | |
| Decision | run_id, event_id, option_id, projection(JSONB), applied_at | |
| Report | run_id, type, content_md, content_json, pdf_path | |
| Scenario | id, author_ws, title, category, payload(JSONB), clones, is_public | marketplace |
| Subscription | workspace_id, stripe_sub_id, tier, status, period_end | |
| UsageRecord | workspace_id, period, runs_used, mc_ticks_used, llm_tokens_used | metering |
| ApiKey | workspace_id, prefix, hash, scopes, rate_limit | enterprise API |

## API Surface (v1)

```
POST   /api/v1/auth/register | /login | /refresh | /verify-email | /forgot-password
GET    /api/v1/users/me                 PATCH /api/v1/users/me
CRUD   /api/v1/workspaces               POST /workspaces/{id}/invites   POST /invites/{token}/accept
CRUD   /api/v1/blueprints               POST /blueprints/{id}/versions  GET /blueprints/{id}/validate
POST   /api/v1/blueprints/{id}/review   → AI Forge review (vulnerabilities)
POST   /api/v1/simulations              → start run (baseline|stress|monte_carlo|ghost)
GET    /api/v1/simulations/{id}         → state + progress
POST   /api/v1/simulations/{id}/control → pause/resume/cancel
GET    /api/v1/simulations/{id}/ticks   → KPI time-series
POST   /api/v1/simulations/{id}/decide  → apply a strategic option to active hurdle
GET    /api/v1/simulations/{id}/report  → resilience audit
POST   /api/v1/simulations/{id}/report/export → PDF
GET    /api/v1/reports/compare?a=..&b=..
CRUD   /api/v1/scenarios                POST /scenarios/{id}/clone  GET /scenarios/featured
GET    /api/v1/leaderboard
POST   /api/v1/billing/checkout         POST /billing/portal  GET /billing/usage
POST   /api/v1/webhooks/stripe
CRUD   /api/v1/api-keys
GET    /api/v1/admin/stats | /admin/users | /admin/workspaces
WS     /ws/simulations/{id}             → live tick/event stream
```

## Task List

Detailed cards live in `tasks/phases/`. Master checklist: `tasks/todo.md`.

### Phase 0 — Scaffolding & DevOps
- [ ] T01: Monorepo skeleton, env config, Makefile, docker-compose (postgres, redis, backend, worker, frontend)
- [ ] T02: Backend scaffold — FastAPI app factory, settings, logging, health endpoint, exception handlers
- [ ] T03: Frontend scaffold — Vite+React+TS, Tailwind, shadcn/ui, router, dark theme shell
- [ ] T04: Database layer — async session, base model, Alembic, initial migration
- [ ] T05: CI — GitHub Actions: backend lint+test, frontend lint+build

### Checkpoint A (after T05): `docker compose up` boots the stack; `/health` returns 200; frontend renders shell; CI green.

### Phase 1 — Auth & Multi-Tenancy
- [ ] T06: User model + register/login/refresh JWT endpoints
- [ ] T07: Auth UI — login/register pages, token handling, protected routes
- [ ] T08: Workspace + membership models, CRUD, RBAC dependency guard
- [ ] T09: Workspace UI — switcher, member management, invite flow
- [ ] T10: Email service abstraction (verification + invite emails, console fallback)

### Phase 2 — Deterministic Simulation Engine (pure Python, no I/O)
- [ ] T11: Engine state dataclasses + blueprint→state compiler
- [ ] T12: Financial calculator (revenue, costs, cash flow, LTV/CAC, runway, MRR/ARR, NRR)
- [ ] T13: Monthly time-step loop with trigger checks (bankruptcy, profitability, milestones)
- [ ] T14: Market dynamics (demand curve, price elasticity, seasonality, competitor pressure)
- [ ] T15: Event injector + golden-path engine test suite (24-month trace)

### Checkpoint B (after T15): engine simulates 24 months from a fixture blueprint in <100ms, 100% deterministic with a seed; unit tests green.

### Phase 3 — Blueprints
- [ ] T16: Blueprint schemas + structural validation service (LTV:CAC, runway, concentration)
- [ ] T17: Blueprint CRUD + versioning API
- [ ] T18: Blueprint Builder UI — guided wizard with live validation feedback
- [ ] T19: Blueprint canvas view (React Flow visual map of the model)

### Phase 4 — AI Cortex
- [x] T20: LLM provider abstraction (OpenAI-compatible, env-configured, retry/timeout/token-cost tracking)
- [x] T21: Structured output bridge — Pydantic schema validation + repair-retry loop
- [x] T22: Forge agent — system prompt, blueprint review endpoint (Format A vulnerabilities)
- [x] T23: Hurdle generator — vital-signs snapshot → Format B hurdle JSON + chronicle memory
- [x] T24: Strategist — branching options + 12-month outcome projection per option

### Checkpoint C (after T24): with `LLM_*` env set, `POST /blueprints/{id}/review` and hurdle generation return schema-valid JSON; with no key, deterministic mock fallback works (dev mode).

### Phase 5 — Simulation Runs
- [ ] T25: Simulation run models + start/state API + baseline run service
- [ ] T26: Stress-test mode — scheduled hurdle injection + decision application
- [ ] T27: Monte Carlo worker (Celery) — N seeded runs, aggregation, Redis progress
- [ ] T28: WebSocket live tick streaming + run controls
- [ ] T29: Simulation Runner UI — live cash curve, event feed, War Room decision modal

### Phase 6 — Reports & Optimization
- [ ] T30: Resilience audit generation (survival rate, kill vectors, ranked weaknesses)
- [ ] T31: Counter-factual analysis + optimization recommendations
- [ ] T32: Report UI + Markdown/PDF export + shareable links
- [ ] T33: Run/blueprint comparison (V1 vs V2)

### Checkpoint D (after T33): full loop works end-to-end — build blueprint → baseline → stress test with decisions → Monte Carlo → report → comparison.

### Phase 7 — App Shell, Dashboard & Marketing
- [x] T34: Design system polish — dark theme tokens, motion, skeletons, empty states
- [x] T35: Main dashboard — KPI cards, resilience gauge, charts, recent activity
- [x] T36: Onboarding wizard (industry / stage / primary fear)
- [x] T37: Notifications center + toast system
- [x] T38: Settings pages (profile, workspace, members, security)
- [x] T39: Marketing landing page + pricing page

### Phase 8 — Monetization & Platform Features
- [x] T40: Stripe billing — plans, checkout, portal, webhooks
- [x] T41: Usage metering + plan limit enforcement + paywall UI
- [x] T42: Scenario marketplace — publish, browse, clone
- [x] T43: Ghost Mode — autonomous AI personality runs + spectator view
- [x] T44: Public leaderboards + shareable report links
- [x] T45: Enterprise API keys + per-key rate limiting
- [x] T46: Admin dashboard (users, workspaces, usage, revenue)

### Phase 9 — Production Hardening
- [ ] T47: Test coverage push — engine ≥90%, API integration ≥80%
- [ ] T48: Observability — request logging, Sentry, Prometheus metrics, readiness probes
- [ ] T49: Security hardening — rate limits, CORS, security headers, audit log
- [ ] T50: Seed data + demo content + documentation (README, docs/)
- [ ] T51: Production deployment — prod Dockerfiles, compose-prod, backups, runbook

### Checkpoint E (after T51): staging deploy passes smoke tests; docs let a new dev run the stack in <15 min.

## Parallelization Opportunities

- After Checkpoint A: Phase 1 (auth) and Phase 2 (engine) are fully independent — parallelize.
- Phase 3 backend (T16–T17) and frontend scaffolds of Phase 7 (T34) can overlap once API contracts in this plan are fixed.
- Phase 4 (T20–T24) needs only the engine state contract (T11) — can start before Phase 3 finishes.
- Frontend feature work (T18, T19, T29, T32, T35) can parallelize once endpoints exist or are mocked.
- Must stay sequential: T04 before any model work; T06 before T08; T11→T12→T13→T15; T25 before T26/T27/T28; T40 before T41.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LLM returns invalid/impossible JSON | High | Structured output bridge (T21) validates every payload; engine clamps deltas to physical possibility; mock provider for dev/test |
| LLM cost/latency at scale | High | 90% of math is deterministic; batch agent calls; cache chronicle summaries; cheapest model tier via env config; token usage metered per workspace |
| Engine-AI contract drift | Med | Format A/B/C JSON schemas are Pydantic models shared by both sides; golden fixture tests pin the contract |
| Stripe webhook complexity | Med | Webhook handler is idempotent, signature-verified, covered by integration tests with Stripe CLI fixtures |
| Scope creep killing delivery | High | Phases 0–6 are the core product; Phases 7–9 are additive and independently shippable — cut from the bottom if needed |
| Cheap LLM weak at long narratives | Med | Keep prompts short with compact vital-signs snapshots; narrative quality prompts isolated in `agents/prompts/` for easy iteration |

## Open Questions

- **Time-series store:** JSONB tick logs in Postgres are planned; introduce InfluxDB/TimescaleDB only if tick volume proves painful (defer to Phase 9 review).
- **Multiplayer competitive market** (plan doc Phase 4): deliberately out of scope for v1 — Ghost Mode covers the "AI opponents" experience at far lower complexity. Confirm?
- **PDF rendering:** WeasyPrint (pure Python, no system browser) vs. Playwright/Chromium (prettier, heavier). Plan assumes WeasyPrint.
- **Email provider:** plan assumes SMTP/console fallback; pick SendGrid/Resend/SES before T10 ships to production.
