# Project Progress — The Forge

Live status tracker for the build. Updated as phases complete; full detail in `tasks/todo.md` and per-phase cards in `tasks/phases/`.

**Last updated:** 2026-08-06

## Summary

| Phase | Scope | Status |
|---|---|---|
| 0 | Scaffolding & DevOps (T01–T05) | Complete |
| 1 | Auth & Multi-Tenancy (T06–T10) | Complete |
| 2 | Deterministic Simulation Engine (T11–T15) | Complete |
| 3 | Blueprints (T16–T19) | Complete |
| 4 | AI Cortex (T20–T24) | Complete |
| 5 | Simulation Runs (T25–T29) | Complete |
| 6 | Reports & Optimization (T30–T33) | **Complete** |
| 7 | App Shell, Dashboard & Marketing (T34–T39) | **Complete** |
| 8 | Monetization & Platform Features (T40–T46) | Not started |
| 9 | Production Hardening (T47–T51) | Not started |

**Next up:** Phase 8 — Monetization & Platform Features (T40–T46).

## Phase 7 — App Shell, Dashboard & Marketing (T34–T39) — Complete ✅

Turned the working core product into a flagship SaaS surface: a dark-first "war room" design system, a real data-driven dashboard, a 3-step onboarding wizard, an app-wide notification/toast layer, full settings pages with password change, and a public marketing site.

### Delivered

- **T34 — Design system polish** — Dark-first ember-tinted palette as CSS custom properties (`tailwind.config.ts` + `globals.css`): `forge` accent, `success`/`warning`/`danger` semantics, `chart-1…5` tokens; self-hosted Space Grotesk (display) + Inter (body) via `@fontsource`. `PageTransition` (framer-motion fade + 8px slide-up, 200ms easeOut, respects `prefers-reduced-motion`) wrapping all `/app` routes. New `Skeleton` + `EmptyState` primitives swept across BlueprintList, SimulationList, Members, and a new ReportsList page (replaces the old ComingSoon placeholder). Removed all hardcoded hex colors from feature components (grep-clean).
- **T35 — Dashboard** (`/app`) — KPI cards (cash, MRR, burn, runway) from the latest completed run's ticks with MoM deltas + inline SVG sparklines; animated `ResilienceGauge` (0–100, <40 Fragile / ≤70 At risk / >70 Resilient); `CashCurve` (AreaChart) + `BurnChart` (ComposedChart) on the chart tokens; recent-runs table with status badges and row-click → run; quick actions (New Blueprint / Run Baseline / Monte Carlo); skeletons while loading and an EmptyState CTA when no runs exist.
- **T36 — Onboarding wizard** — 3-step wizard (`/onboarding`): industry card-grid (8 options), stage (Idea→Series A+), primary fear textarea with suggestion chips (min 10 chars); persists via `PATCH /users/me` and invalidates the `["me"]` cache. Backend: `industry`/`stage`/`primary_fear`/`onboarding_completed` columns on `User` (migration `f7a8b9c0d1e2`), `UserUpdate`/`UserRead` schemas, PATCH auto-flips `onboarding_completed` when all three fields set. `RequireOnboarding` gate redirects to `/onboarding`; "Skip for now" sets a localStorage flag.
- **T37 — Notifications + toasts** — `sonner` Toaster mounted in AppShell; `lib/toast.ts` (`toastSuccess/Error/Info`) wired into simulation start, blueprint save, report export mutations; Zustand `notifications` store with `persist` (capped at 50); `NotificationBell` in Topbar with unread badge, popover list (bold+dot for unread, click-to-read, mark-all-read, clear, empty state).
- **T38 — Settings** (`/app/settings/*`) — `SettingsLayout` sub-nav: Profile (name + onboarding fields, `PATCH /users/me`), Workspace (rename, disabled + note for member role), Members (invite/role/remove with toasts + skeletons), Security (password change via new `POST /users/me/password` → 204/400, `PasswordChange` schema, `change_password` in `auth_service`).
- **T39 — Marketing** — Public `/` (LandingPage: Hero with ember glow + staggered fade-up, HowItWorks 4 steps, Features cards, marked placeholder SocialProof, FinalCta + footer) and `/pricing` (monthly/yearly toggle, 2 months free, `PLAN_TIERS` in `lib/constants.ts`, highlighted Pro card, CTA → `/register?plan={id}`), all wrapped in `MarketingLayout`; dashboard stays at `/app` with no route conflicts (router test asserts both).

### Verification

- `cd backend && pytest` → **282 passed** (8 new phase-7 tests: onboarding PATCH flow + 4 password-change tests)
- `cd backend && ruff check app tests && mypy app` → **clean**
- `alembic upgrade head` / `downgrade -1` → clean through `f7a8b9c0d1e2` (onboarding fields)
- `cd frontend && npx vitest run` → **36 passed across 11 files** (new: PageTransition, EmptyState, DashboardPage, ResilienceGauge, OnboardingWizard, notifications store, NotificationBell, SecurityPage, LandingPage, PricingPage, router)
- `cd frontend && npm run lint && npm run build` → lint 0 errors (4 pre-existing react-refresh warnings), build ok
- Frontend test tooling added (vitest 3 + RTL + jsdom + setup with IntersectionObserver mock); `npm run test` script added

## Checkpoint D — End-to-end core loop ✅

Build blueprint → baseline run → stress test with decisions → Monte Carlo → resilience report → V1/V2 comparison all work together. Verified end-to-end: blueprint → 2 Monte Carlo runs → enriched Format C report (AI optimizations + counter-factual insight) → compare verdict + kill-vector deltas.

## Phase 6 — Reports & Optimization (T30–T33) — Complete ✅

Completed Monte Carlo runs become the Format C Resilience Audit: deterministic survival metrics, AI-ranked weaknesses, counter-factual "what-if" re-runs with optimization recommendations, Markdown/PDF export, shareable public links, and a V1-vs-V2 comparison.

### Delivered

- **T30 — Resilience audit generation**
  - `Report` model (`app/models/report.py` — id, run_id FK, type, content_md, content_json, pdf_path) + Alembic migration `e5f6a7b8c9d0`
  - `app/services/report_service.py` — `generate_resilience_audit` reads the T27 `MonteCarloResult` from `SimulationRun.result`, computes survival rate / median lifespan / ranked kill vectors (% of failures), merges Format A vulnerabilities + resilience_score into severity-ranked weaknesses
  - Deterministic SURVIVAL METRICS + ARCHITECTURAL WEAKNESSES markdown (no LLM); `GET /api/v1/reports/simulations/{run_id}/report` idempotent, 404 cross-workspace, 409 non-completed

- **T31 — Counter-factual analysis + post-mortem**
  - `app/services/optimization_service.py` — 6 fixed tweaks (churn −20%, cac −20%, price +10%, fixed_monthly −15%, starting_capital +25%, client_concentration capped at 25%); `estimate_survival_delta` seeded-deterministic pure engine (`seed + tweak_index*1000 + run_index`)
  - `app/agents/post_mortem.py` + `prompts/post_mortem.md` — bridge-validated `PostMortemOutput`; the "Impact on Survival Rate" column ALWAYS comes from engine deltas; invalid LLM output falls back to a deterministic engine-delta table; mock provider canned output keeps the no-key flow green
  - Reports auto-enrich on first GET with `### AI-GENERATED OPTIMIZATIONS` (table) + `### COUNTER-FACTUAL INSIGHT`

- **T32 — Report UI + export/share**
  - `app/utils/pdf.py` — WeasyPrint + markdown → dark-styled PDF bytes
  - `POST /report/export` → 201 `{pdf_url}` (saved under `REPORT_STORAGE_DIR`, `Report.pdf_path` set)
  - `POST /report/share` → signed itsdangerous token (7-day); public `GET /api/v1/reports/shared/{token}` → 200, 410 expired, 404 tampered
  - Frontend `features/reports/`: `ReportPage` (stat cards, weakness severity colors, optimization table, ReactMarkdown full report), `SharedReportPage` at public `/reports/shared/:token`, Export PDF + Copy share-link buttons; `react-markdown` added

- **T33 — Run/blueprint comparison**
  - `GET /api/v1/reports/compare?a=&b=` → `ComparisonResponse` (RunSummary × 2, deltas, kill_vector_changes sorted by |Δpp|, verdict per ±1pp rule); 404 foreign/missing, 409 non-completed
  - `GET /api/v1/simulations` list endpoint added for the picker
  - Frontend `ComparePage` at `/reports/compare` — two run pickers, side-by-side metric cards, kill-vector delta table, verdict banner

### Verification

- `cd backend && pytest` → **274 passed** (36 new phase-6 tests: report service math/markdown/idempotency, optimization determinism, post-mortem fallback, PDF bytes, export/share round-trip, tampered/expired tokens, compare deltas/verdict/404/409)
- `cd backend && ruff check app tests && mypy app` → **clean** (mypy overrides added for weasyprint/markdown)
- `alembic upgrade head` → clean through `e5f6a7b8c9d0` (reports table)
- `cd frontend && npm run build && npm run lint` → build ok (react-markdown added), lint 0 errors (1 pre-existing react-refresh warning)

## Phase 5 — Simulation Runs (T25–T29) — Complete ✅

The deterministic engine is wired to the API: runs and tick logs are persisted, AI hurdles are injected with user decisions, Monte Carlo batches run through Celery, ticks stream over WebSocket, and the live Simulation Runner UI drives it all.

### Delivered

- **T25 — Run models + baseline service + API** — `SimulationRun`/`TickLog`/`SimulationEvent`/`Decision` models + `RunStatus` enum, `app/engine/metrics.py` (shared KPI shape + resilience_score), seeded deterministic baseline runner, `POST/GET /api/v1/simulations` + `GET /ticks`, migration `c7d2e8f1a3b4`.
- **T26 — Stress mode + decisions** — deterministic per-seed hurdle schedules, engine-segment advancement, Hurdle Generator + Strategist injection (keyless mock fallback), parked state_snapshot, `POST /decide` with 409/422 guards.
- **T27 — Monte Carlo worker** — LLM-free deterministic templates, `aggregate_results` (survival rate, percentiles, kill vectors), Redis progress + cancel flag, 202/pending enqueue flow.
- **T28 — WebSocket + controls** — `/ws/simulations/{id}` (token auth, snapshot + replay + pub/sub forward), `POST /control` pause/resume/cancel.
- **T29 — Runner UI** — Recharts cash curve, live feed, War Room decision modal, Zustand store, socket hook with backoff reconnect.

### Verification

- 238 backend tests pass, ruff + mypy clean, `alembic upgrade head` clean, frontend build + lint pass. Full flow verified: baseline → stress → decide → Monte Carlo with deterministic results.

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

cd ../frontend
npm run build                       # type-check + bundle
npm run lint                        # eslint
```

Full-stack (requires Docker): `docker compose up -d` then `curl localhost:8000/health`.
