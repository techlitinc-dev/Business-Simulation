# Phase 8 — Monetization & Platform Features

Adds the commercial SaaS layer on top of the working simulation product: Stripe billing (T40), usage metering with plan-limit paywalls (T41), the scenario marketplace (T42), Ghost Mode autonomous runs (T43), public leaderboards and shared report pages (T44), enterprise API keys (T45), and the admin dashboard (T46).

## Task T40: Stripe billing — plans, checkout, customer portal, idempotent webhook handler

**Description:** Wire Stripe subscriptions into the platform. Add a `PLANS` constant to `app/core/config.py` (or a small `app/services/plans.py` module imported by config) describing three tiers — `free`, `pro`, `enterprise` — each with `stripe_price_id` (from env: `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_ENTERPRISE_MONTHLY`; `free` has none), monthly `price_usd`, and limits consumed later by T41: `runs_per_month`, `monte_carlo_runs_per_batch`, `llm_tokens_per_month`, `seats`. Suggested values: free `{runs: 3, mc: 25, tokens: 50_000, seats: 1, $0}`, pro `{runs: 50, mc: 500, tokens: 2_000_000, seats: 5, $49}`, enterprise `{runs: -1 (unlimited), mc: -1, tokens: -1, seats: -1, $499}`. Use the official `stripe` Python SDK (pin `stripe>=7,<9` in `requirements.txt`), env-configured via `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and `FRONTEND_URL` (for success/cancel redirect URLs) in pydantic-settings. Create the `Subscription` model in `app/models/billing.py` per the plan data model: `id`, `workspace_id` (FK, unique), `stripe_customer_id`, `stripe_subscription_id` (unique, nullable), `tier` (str: free/pro/enterprise, default "free"), `status` (str: active/trialing/past_due/canceled), `current_period_end` (datetime, nullable) — plus an Alembic migration. Implement `app/services/billing_service.py` with `create_checkout_session(workspace, tier) -> str`, `create_portal_session(workspace) -> str`, and `handle_webhook_event(event: dict)`. Endpoints in `app/api/v1/endpoints/billing.py`: `POST /api/v1/billing/checkout` body `CheckoutRequest{tier: Literal["pro","enterprise"]}` → 200 `CheckoutResponse{checkout_url}` (creates/loads the Stripe customer, stores `stripe_customer_id` on the Workspace); `POST /api/v1/billing/portal` → 200 `PortalResponse{portal_url}` (404 if workspace has no Stripe customer); `GET /api/v1/billing/subscription` → 200 `SubscriptionResponse{tier, status, current_period_end}`. Webhook in `app/api/v1/endpoints/webhooks.py`: `POST /api/v1/webhooks/stripe` — read the raw request body, verify the `Stripe-Signature` header with `stripe.Webhook.construct_event(..., STRIPE_WEBHOOK_SECRET)` (400 on bad signature), enforce idempotency with Redis `SETNX stripe:webhook:{event.id}` TTL 24h (duplicate delivery → 200 `{received: true, duplicate: true}` without side effects), then dispatch: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted` → upsert the `Subscription` row mapping `price_id` → tier and Stripe status → status; `invoice.payment_failed` → set status `past_due`. Unknown event types → 200 `{received: true}`. Schemas in `app/schemas/billing.py` (Pydantic v2). Frontend: in `frontend/src/features/billing/` make the existing PricingPage (from T39) upgrade buttons call `POST /billing/checkout` via TanStack Query mutation and `window.location.assign(checkout_url)`; handle `?checkout=success|canceled` query param on return with a toast. When `STRIPE_SECRET_KEY` is empty (dev/test), the service must raise a clear 503 "billing not configured" on checkout/portal, and tests must mock the `stripe` module — never hit the network.

**Acceptance criteria:**
- [ ] `POST /api/v1/billing/checkout` with `{tier: "pro"}` returns 200 `{"checkout_url": "https://checkout.stripe.com/..."}` and persists `stripe_customer_id` on the workspace (stripe SDK mocked in tests)
- [ ] `POST /api/v1/webhooks/stripe` with an invalid signature returns 400; with a valid signature and a `customer.subscription.updated` event it upserts the `Subscription` row (tier + status + `current_period_end`)
- [ ] Re-delivering the same webhook event id returns 200 with `{"duplicate": true}` and does not modify the `Subscription` row a second time (idempotency verified by asserting DB state unchanged)
- [ ] `POST /api/v1/billing/portal` returns 404 for a workspace with no Stripe customer and 200 `{portal_url}` otherwise
- [ ] `GET /api/v1/billing/subscription` on a fresh workspace returns 200 with `tier: "free"`
- [ ] All new routes require an authenticated workspace member (401 without token)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_billing_service.py tests/integration/api/test_billing.py tests/integration/api/test_stripe_webhook.py -v` (create all three files; mock `stripe` SDK and Redis)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run build && npm run lint`
- [ ] Manual check: with Stripe CLI `stripe trigger customer.subscription.updated` against a locally running stack, the workspace subscription row flips tier/status in the DB

**Dependencies:** T08

**Files likely touched:**
- `backend/app/core/config.py`
- `backend/app/models/billing.py`
- `backend/app/schemas/billing.py`
- `backend/app/services/billing_service.py`
- `backend/app/api/v1/endpoints/billing.py`
- `backend/app/api/v1/endpoints/webhooks.py`
- `backend/app/api/v1/router.py`
- `backend/alembic/versions/<new>_subscriptions.py`
- `backend/requirements.txt`
- `backend/tests/unit/services/test_billing_service.py`
- `backend/tests/integration/api/test_billing.py`
- `backend/tests/integration/api/test_stripe_webhook.py`
- `frontend/src/features/billing/PricingPage.tsx`
- `.env.example`

**Estimated scope:** L

## Task T41: Usage metering + plan-limit enforcement + paywall/upgrade UI

**Description:** Meter per-workspace consumption and hard-enforce the plan limits defined in T40's `PLANS` config. Add the `UsageRecord` model to `app/models/billing.py` (+ Alembic migration): `id`, `workspace_id` (FK), `period` (str `"YYYY-MM"`), `runs_used` (int, default 0), `mc_ticks_used` (int, default 0 — counts Monte Carlo simulations executed), `llm_tokens_used` (int, default 0); unique constraint on `(workspace_id, period)`. Implement `app/services/metering_service.py` with async functions `get_current_usage(db, workspace_id) -> UsageRecord` (get-or-create for the current UTC month), `increment(db, workspace_id, metric: Literal["runs","mc_ticks","llm_tokens"], amount: int = 1)`, and `check_limit(db, workspace_id, metric) -> None` which raises a new domain exception `PlanLimitExceeded(metric, limit, used, tier)` (add it in `app/core/exceptions.py` with a handler returning **402 Payment Required** and body `{"detail": "...", "code": "plan_limit_exceeded", "metric", "limit", "used", "tier"}`; a limit of `-1` means unlimited). Expose a FastAPI dependency factory `enforce_plan_limit(metric)` in `app/api/deps.py` that runs `check_limit` before the endpoint and increments after success — wire it into the simulation-start endpoint from T25 (`POST /api/v1/simulations`, metric `"runs"`) and into Monte Carlo batch creation from T27 (metric `"mc_ticks"`, amount = N runs requested). LLM tokens: after every agent call, the LLM provider from T20 already tracks `prompt_tokens + completion_tokens` on `LLMResponse`; call `metering_service.increment(..., "llm_tokens", tokens)` from `app/agents/bridge.py` (inject the workspace_id via the calling service) so every validated LLM call is metered. Endpoint `GET /api/v1/billing/usage` (in `endpoints/billing.py`) → 200 `UsageResponse{tier, period, usage: {runs_used, mc_ticks_used, llm_tokens_used}, limits: {runs_per_month, monte_carlo_runs_per_batch, llm_tokens_per_month, seats}}`. Frontend (`frontend/src/features/billing/`): a `UsageMeters.tsx` component (progress bars per metric, TanStack Query on `GET /billing/usage`) rendered on a billing settings page, and a `PaywallModal.tsx` (shadcn/ui Dialog: "You've reached your {metric} limit on the {tier} plan" + Upgrade button linking to PricingPage); add a 402 interceptor in `frontend/src/lib/api-client.ts` that opens the modal via a small Zustand store (`frontend/src/stores/billing.ts`) instead of throwing a generic error.

**Acceptance criteria:**
- [ ] `GET /api/v1/billing/usage` returns 200 with the current-month counters and the limits for the workspace's tier
- [ ] Starting a simulation run increments `runs_used` by 1 in the current-period `UsageRecord` row (row created on first use)
- [ ] On a `free` workspace with `runs_used == 3`, `POST /api/v1/simulations` returns 402 with `code: "plan_limit_exceeded"` and `metric: "runs"`
- [ ] The same request on a workspace whose subscription is `pro` succeeds (402 is tier-dependent, driven by `PLANS` config, not hardcoded)
- [ ] A metered agent call through `bridge.py` increases `llm_tokens_used` by exactly the token count reported by the (mock) provider
- [ ] Frontend: forcing a 402 response opens the paywall modal with the metric name and an upgrade link (component test or manual check)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_metering_service.py tests/integration/api/test_usage_limits.py -v` (create both files)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run build && npm run lint`
- [ ] Manual check: seed a free workspace to its run limit, attempt a run in the UI, observe the paywall modal and the 402 in the network tab

**Dependencies:** T40, T25

**Files likely touched:**
- `backend/app/models/billing.py`
- `backend/app/services/metering_service.py`
- `backend/app/core/exceptions.py`
- `backend/app/api/deps.py`
- `backend/app/api/v1/endpoints/billing.py`
- `backend/app/api/v1/endpoints/simulations.py`
- `backend/app/agents/bridge.py`
- `backend/app/schemas/billing.py`
- `backend/alembic/versions/<new>_usage_records.py`
- `backend/tests/unit/services/test_metering_service.py`
- `backend/tests/integration/api/test_usage_limits.py`
- `frontend/src/features/billing/UsageMeters.tsx`
- `frontend/src/features/billing/PaywallModal.tsx`
- `frontend/src/lib/api-client.ts`
- `frontend/src/stores/billing.ts`

**Estimated scope:** M

## Task T42: Scenario marketplace — publish, browse/featured, clone

**Description:** Let workspaces publish blueprint payloads as reusable, browsable scenario templates (per spec §9 Phase 6: "Pre-built disasters based on real case studies (2008 Crash, COVID-19, dot-com bust)"). Create `app/models/scenario.py`: `Scenario` with `id` (prefixed `scn_` via `app/utils/ids.py`), `author_workspace_id` (FK), `title` (str, ≤120 chars), `description` (str, ≤2000), `category` (str enum: `market_crash`, `competitor_attack`, `supply_chain`, `regulatory`, `pandemic`, `custom`), `payload` (JSONB — a valid Format A blueprint payload, reusing the `BlueprintPayload` Pydantic schema from T16 for validation), `clones_count` (int, default 0), `is_public` (bool, default true), `is_featured` (bool, default false — admin-set), `created_at`; plus an Alembic migration. Service `app/services/scenario_service.py`: `publish`, `list_public(category: str | None, page, page_size=20)`, `get`, `clone_to_workspace(scenario_id, workspace_id)` (creates a new `Blueprint` + `BlueprintVersion` owned by the caller's workspace with `payload` copied, name = scenario title, and atomically increments `clones_count`), `unpublish` (author or admin only, sets `is_public=false`). Endpoints in `app/api/v1/endpoints/scenarios.py` with schemas in `app/schemas/scenario.py`: `POST /api/v1/scenarios` body `ScenarioCreate{title, description, category, blueprint_version_id}` → 201 `ScenarioResponse` (validates the version's payload, 404 if the version isn't in the caller's workspace); `GET /api/v1/scenarios?category=&page=` → 200 `ScenarioListResponse{items: ScenarioSummary[], total, page}` (public scenarios only, no auth required for browsing); `GET /api/v1/scenarios/featured` → 200 `ScenarioSummary[]` where `is_featured=true` (no auth); `GET /api/v1/scenarios/{id}` → 200 `ScenarioResponse` (404 if not public and caller isn't the author); `POST /api/v1/scenarios/{id}/clone` → 201 `{blueprint_id, blueprint_version_id}` (auth required, 404 for non-public); `DELETE /api/v1/scenarios/{id}` → 204 (author workspace or `is_admin`, else 403). Frontend `frontend/src/features/marketplace/`: `MarketplacePage.tsx` (category filter tabs + paginated grid of `ScenarioCard.tsx`, TanStack Query), `ScenarioDetailPage.tsx` (payload summary + Clone button → navigates to the cloned blueprint), and a `PublishScenarioModal.tsx` on the blueprint page (pick version, set title/category/description).

**Acceptance criteria:**
- [ ] `POST /api/v1/scenarios` with a valid `blueprint_version_id` returns 201 and the stored `payload` deep-equals the blueprint version's payload
- [ ] `GET /api/v1/scenarios?category=market_crash` returns only public scenarios of that category with correct `total`/pagination, and requires no auth token
- [ ] `GET /api/v1/scenarios/featured` returns only `is_featured=true` scenarios
- [ ] `POST /api/v1/scenarios/{id}/clone` returns 201, creates a `Blueprint` + version 1 `BlueprintVersion` in the caller's workspace, and increments `clones_count` by exactly 1 (two clones → 2)
- [ ] Non-author, non-admin caller gets 404 on `GET` of a non-public scenario and 403 on `DELETE` of someone else's public scenario
- [ ] Cloned blueprint appears in the caller's blueprint list and passes structural validation

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_scenario_service.py tests/integration/api/test_scenarios.py -v` (create both files)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run build && npm run lint`
- [ ] Manual check: publish a scenario from a blueprint, browse it in an incognito window (no login), clone it while logged in, and see it in "My Blueprints"

**Dependencies:** T17

**Files likely touched:**
- `backend/app/models/scenario.py`
- `backend/app/schemas/scenario.py`
- `backend/app/services/scenario_service.py`
- `backend/app/api/v1/endpoints/scenarios.py`
- `backend/app/api/v1/router.py`
- `backend/alembic/versions/<new>_scenarios.py`
- `backend/tests/unit/services/test_scenario_service.py`
- `backend/tests/integration/api/test_scenarios.py`
- `frontend/src/features/marketplace/MarketplacePage.tsx`
- `frontend/src/features/marketplace/ScenarioCard.tsx`
- `frontend/src/features/marketplace/ScenarioDetailPage.tsx`
- `frontend/src/features/marketplace/PublishScenarioModal.tsx`
- `frontend/src/router.tsx`

**Estimated scope:** M

## Task T43: Ghost Mode — autonomous AI personality runs + spectator UI

**Description:** Implement spec §9 Phase 6 Ghost Mode: "AI runs the business autonomously with different 'personalities' (Aggressive, Conservative, Opportunist)". A ghost run is a stress-test run (T26) where every hurdle decision is made automatically by `app/agents/ghost.py` instead of the user. Create `GhostAgent` in `app/agents/ghost.py` with constructor `GhostAgent(provider: LLMProvider, bridge: StructuredOutputBridge, personality: GhostPersonality)` where `GhostPersonality = Literal["aggressive", "conservative", "opportunist"]`; method `async choose_option(hurdle: FormatBHurdle, state_snapshot: dict) -> GhostDecision`. It MUST go through the provider abstraction + bridge: the prompt (`app/agents/prompts/ghost_personality.md`, one template with a `{{personality}}` section) asks the LLM to pick among the hurdle's Format B `strategic_options`, validated by the bridge against this Pydantic schema:

```python
class GhostDecision(BaseModel):
    option_id: str            # must be one of the hurdle's strategic_options option_ids
    rationale: str            # <= 500 chars, shown in the spectator feed
```

Deterministic behavior without an API key: the mock provider (T20) returns a fixed valid JSON, and `ghost.py` then applies a personality rule on the validated options as a deterministic fallback/override so tests are stable — `aggressive`: pick the option with the highest `probability_success` (ties → highest `cash_impact_monthly`); `conservative`: pick the option with the smallest negative `cash_impact_monthly` (ties → highest `probability_success`); `opportunist`: pick the option maximizing `probability_success * cash_impact_monthly` (expected value). Enforce the rule-based choice whenever the LLM/mock output's `option_id` is valid but deviates in mock mode; in live mode trust the LLM's pick. `app/services/ghost_service.py`: `start_ghost_run(workspace, blueprint_version_id, personality, seed) -> SimulationRun` reusing T26's stress-test machinery with `mode="ghost"` and `config={"personality": ..., "autoplay": true}`; after each hurdle injection it calls `GhostAgent.choose_option` and applies the decision through the existing `decision_service` (T26), recording the `Decision` with `option_id` and storing `{"actor": "ghost", "personality": ..., "rationale": ...}` in the decision's `projection`/payload; the loop runs to 24 months or bankruptcy with no user input. API surface: extend `POST /api/v1/simulations` (from T25) to accept `mode="ghost"` with `config.personality` required (422 if missing/invalid); state/progress/tick endpoints and the WebSocket stream (T28) work unchanged. Frontend `frontend/src/features/ghost/`: `GhostSetupPage.tsx` (blueprint picker + three personality cards describing each style → `POST /simulations` with `mode: "ghost"`), and `GhostSpectatorPage.tsx` — a read-only variant of the T29 runner view reusing the live cash curve and event feed, with decision entries rendered as "{personality} chose {option name}: {rationale}" and no decision modal; add routes in `router.tsx` and a "Watch Ghost Run" entry point from the simulation list.

**Acceptance criteria:**
- [ ] `POST /api/v1/simulations` with `mode: "ghost"` and `config: {"personality": "aggressive"}` returns 201 and the run progresses to `completed` (or `bankrupt`) with zero calls to `POST /simulations/{id}/decide`
- [ ] `mode: "ghost"` without `config.personality` (or with an invalid one) returns 422
- [ ] With the mock provider, two ghost runs with the same seed and personality produce identical decision sequences and identical final KPI traces (deterministic)
- [ ] In mock mode, given a hurdle with options of differing `probability_success`/`cash_impact_monthly`, each personality picks the option its rule dictates (unit test with a crafted Format B fixture)
- [ ] Every hurdle in a completed ghost run has a `Decision` row whose payload contains `actor: "ghost"`, the personality, and a non-empty `rationale`
- [ ] Spectator page renders the ghost run's decision feed with rationale text and offers no decision inputs

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/agents/test_ghost.py tests/unit/services/test_ghost_service.py -v` (create both files; use the deterministic mock provider only)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run build && npm run lint`
- [ ] Manual check: start a Conservative ghost run from the UI, watch the spectator view auto-play decisions to month 24, reload mid-run and confirm the stream resumes

**Dependencies:** T26, T24

**Files likely touched:**
- `backend/app/agents/ghost.py`
- `backend/app/agents/prompts/ghost_personality.md`
- `backend/app/services/ghost_service.py`
- `backend/app/api/v1/endpoints/simulations.py`
- `backend/app/schemas/simulation.py`
- `backend/tests/unit/agents/test_ghost.py`
- `backend/tests/unit/services/test_ghost_service.py`
- `frontend/src/features/ghost/GhostSetupPage.tsx`
- `frontend/src/features/ghost/GhostSpectatorPage.tsx`
- `frontend/src/router.tsx`

**Estimated scope:** L

## Task T44: Public leaderboards + shareable report pages

**Description:** Add a public leaderboard of the most resilient businesses and unauthenticated shareable report pages. Leaderboard data source: completed Monte Carlo runs whose resilience audit (T30) was generated. Add a nullable `is_public` boolean (default `false`) column to `SimulationRun` (+ Alembic migration) — settable via `PATCH /api/v1/simulations/{id}` body `SimulationVisibilityUpdate{is_public: bool}` → 200 (owner workspace only, 403 otherwise). The resilience score is already computed by `app/engine/metrics.py` (T15/T30) and stored in `SimulationRun.result` JSONB as `result["resilience_score"]` alongside `result["survival_rate"]` and `result["median_lifespan_months"]` — this task reads those fields, never recomputes them. Endpoint `GET /api/v1/leaderboard?limit=50` (no auth required) → 200 `LeaderboardResponse{entries: LeaderboardEntry[]}` where each entry is `{rank, run_id, workspace_name, blueprint_name, resilience_score, survival_rate, median_lifespan_months, completed_at}`, filtered to `mode="monte_carlo" AND status="completed" AND is_public=true`, ordered by `resilience_score` DESC, `survival_rate` DESC, rank assigned sequentially starting at 1. Shareable reports: T32 created share links; if (and only if) it did not, add a `share_token` (URL-safe random, unique, indexed) column to `Report`; expose `GET /api/v1/reports/shared/{token}` (no auth) → 200 `SharedReportResponse{blueprint_name, completed_at, content_md, content_json}` and 404 for unknown tokens; the authenticated owner can rotate/revoke via `POST /api/v1/simulations/{id}/report/share` → 200 `{share_url}` and `DELETE .../report/share` → 204. Frontend: `frontend/src/features/leaderboard/LeaderboardPage.tsx` (public route, shadcn/ui table with rank medals for top 3, TanStack Query, links to shared report when the run has one); `frontend/src/features/reports/SharedReportPage.tsx` at route `/shared/reports/:token` — renders the Format C markdown report (survival metrics, architectural weaknesses, optimizations table, counter-factual insight) outside the authenticated AppShell, with a subtle "Simulated in The Forge" footer linking to the landing page; add a "Copy share link" action to the report page (T32) hitting the share endpoint.

**Acceptance criteria:**
- [ ] `GET /api/v1/leaderboard` returns 200 without an auth token, includes only completed, public Monte Carlo runs, and is strictly ordered by descending `resilience_score` with sequential ranks
- [ ] A run with `is_public=false` never appears in the leaderboard; toggling via `PATCH /api/v1/simulations/{id}` as a non-member returns 403
- [ ] `GET /api/v1/reports/shared/{token}` returns 200 with the report markdown without auth, and 404 for an unknown or revoked token
- [ ] `DELETE .../report/share` invalidates the token (subsequent public GET → 404) while the authenticated report endpoint still works
- [ ] SharedReportPage renders without login and contains no links into authenticated routes except the marketing landing page

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/api/test_leaderboard.py tests/integration/api/test_shared_reports.py -v` (create both files)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run build && npm run lint`
- [ ] Manual check: in an incognito window, open `/leaderboard`, click through to a shared report, and confirm no login is requested

**Dependencies:** T30

**Files likely touched:**
- `backend/app/models/simulation.py`
- `backend/app/models/report.py`
- `backend/app/api/v1/endpoints/simulations.py`
- `backend/app/api/v1/endpoints/reports.py`
- `backend/app/api/v1/endpoints/leaderboard.py` (new, or a route in `reports.py` — one file only)
- `backend/app/schemas/simulation.py`
- `backend/app/schemas/report.py`
- `backend/app/api/v1/router.py`
- `backend/alembic/versions/<new>_leaderboard_share.py`
- `backend/tests/integration/api/test_leaderboard.py`
- `backend/tests/integration/api/test_shared_reports.py`
- `frontend/src/features/leaderboard/LeaderboardPage.tsx`
- `frontend/src/features/reports/SharedReportPage.tsx`
- `frontend/src/router.tsx`

**Estimated scope:** M

## Task T45: Enterprise API keys + per-key rate limiting

**Description:** Give enterprise workspaces programmatic access via long-lived API keys as an alternative to JWT auth. Create `app/models/api_key.py`: `ApiKey` with `id` (prefixed `key_`), `workspace_id` (FK), `name` (str), `prefix` (first 12 chars of the key, indexed — for display and rate-limit bucketing), `key_hash` (str — SHA-256 hex of the full key; never store plaintext), `scopes` (JSONB list of strings from `{runs:read, runs:write, reports:read, blueprints:read}`), `rate_limit_rpm` (int, default 60), `last_used_at` (datetime, nullable), `revoked_at` (datetime, nullable), `created_at`; plus an Alembic migration. Key generation in `app/services/api_key_service.py`: full key = `"fk_" + secrets.token_urlsafe(32)`; store `prefix = full_key[:12]` and `key_hash = hashlib.sha256(full_key.encode()).hexdigest()`; the plaintext is returned exactly once in the create response. Endpoints in `app/api/v1/endpoints/api_keys.py` (JWT-authenticated, workspace admin/owner only): `POST /api/v1/api-keys` body `ApiKeyCreate{name, scopes, rate_limit_rpm?}` → 201 `ApiKeyCreatedResponse{id, name, prefix, scopes, key}` (plaintext shown once); `GET /api/v1/api-keys` → 200 `ApiKeyResponse[]` (never includes hash or plaintext); `DELETE /api/v1/api-keys/{id}` → 204 (sets `revoked_at`). Auth: add `get_api_key_workspace` to `app/api/deps.py` — when an `X-API-Key` header is present, hash it, look up by `key_hash`, reject with 401 if unknown or revoked, update `last_used_at`, and return the workspace; endpoints that support programmatic access (start simulation, get run state, get report) accept either JWT or API key via a `get_current_principal` dependency that tries JWT first then falls back to `X-API-Key`. Scope enforcement: dependency factory `require_scope(scope: str)` in `deps.py` returning 403 `{"detail": "missing scope: ..."}` when the key lacks the scope (JWT users implicitly have all scopes). Per-key rate limiting: middleware in `app/core/rate_limit.py` — on requests carrying `X-API-Key`, use Redis `INCR ratelimit:apikey:{prefix}:{epoch_minute}` with `EXPIRE 61` on first increment; when the counter exceeds the key's `rate_limit_rpm`, return 429 with `Retry-After: <seconds until next minute>` and body `{"detail": "rate limit exceeded", "code": "rate_limited"}`. Schemas in `app/schemas/auth.py` or a new `app/schemas/api_key.py` (match the existing convention).

**Acceptance criteria:**
- [ ] `POST /api/v1/api-keys` returns 201 with a plaintext key starting with `fk_`; the DB row stores only the 12-char prefix and a 64-char SHA-256 hex hash (plaintext never persisted)
- [ ] A request to a supported endpoint with header `X-API-Key: <valid key>` authenticates as the key's workspace and returns the same payload as JWT auth
- [ ] A revoked key returns 401; a valid key calling an endpoint requiring a scope it lacks returns 403 with `missing scope` in the detail
- [ ] With `rate_limit_rpm` set to 5, the 6th request within one minute returns 429 with a `Retry-After` header, and requests succeed again after the minute window rolls over (Redis mocked/freezegun in tests)
- [ ] `GET /api/v1/api-keys` response contains no `key_hash` and no plaintext key fields

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_api_key_service.py tests/integration/api/test_api_keys.py -v` (create both files)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: create a key in the settings UI (or via curl), then `curl -H "X-API-Key: fk_..." localhost:8000/api/v1/simulations` and observe a 200, then revoke and observe 401

**Dependencies:** T08

**Files likely touched:**
- `backend/app/models/api_key.py`
- `backend/app/schemas/api_key.py` (or `backend/app/schemas/auth.py`)
- `backend/app/services/api_key_service.py`
- `backend/app/api/v1/endpoints/api_keys.py`
- `backend/app/api/deps.py`
- `backend/app/core/rate_limit.py`
- `backend/app/api/v1/router.py`
- `backend/alembic/versions/<new>_api_keys.py`
- `backend/tests/unit/services/test_api_key_service.py`
- `backend/tests/integration/api/test_api_keys.py`
- `frontend/src/features/settings/ApiKeysPanel.tsx` (create/list/revoke + one-time plaintext reveal dialog)

**Estimated scope:** M

## Task T46: Admin dashboard — users, workspaces, usage, revenue stats

**Description:** Build the internal admin back-office. Backend: add a `require_admin` dependency in `app/api/deps.py` that returns 403 unless `current_user.is_admin` is true (the `User` model already has `is_admin` from T06; promote admins via direct DB update — no UI for granting admin). Implement `app/services/admin_service.py` computing aggregates with SQLAlchemy `func.count`/`func.sum` queries, and `app/api/v1/endpoints/admin.py` with schemas in `app/schemas/admin.py`: `GET /api/v1/admin/stats` → 200 `AdminStatsResponse`:

```json
{
  "total_users": 0, "users_last_30d": 0,
  "total_workspaces": 0, "workspaces_last_30d": 0,
  "subscriptions_by_tier": {"free": 0, "pro": 0, "enterprise": 0},
  "mrr_estimate_usd": 0,
  "runs_this_month": 0, "monte_carlo_ticks_this_month": 0, "llm_tokens_this_month": 0
}
```

`mrr_estimate_usd` is computed as count of `status="active"` subscriptions per tier × the tier's `price_usd` from the T40 `PLANS` config (never hardcode prices in the query). Also `GET /api/v1/admin/users?page=&q=` → 200 `AdminUserListResponse{items: [{id, email, name, is_admin, is_verified, created_at, workspace_count}], total, page}` (case-insensitive email substring search via `q`, page_size 20) and `GET /api/v1/admin/workspaces?page=` → 200 `AdminWorkspaceListResponse{items: [{id, name, slug, plan_tier, member_count, runs_count, created_at}], total, page}`. Monthly usage aggregates come from summing `UsageRecord` rows for the current period (T41); if T41 is not yet merged, return zeros for the three usage fields behind a clearly named helper so the endpoint still works. All three routes require `require_admin` → 403 for non-admins, 401 unauthenticated. Frontend: place the admin UI under `frontend/src/features/settings/admin/` (the plan tree has no dedicated admin feature dir — keep it inside `settings/`): `AdminDashboardPage.tsx` (stat cards from `GET /admin/stats`: users, workspaces, MRR, runs, LLM tokens; a subscriptions-by-tier bar chart with Recharts), `AdminUsersPage.tsx` and `AdminWorkspacesPage.tsx` (paginated shadcn/ui tables, search box for users). Gate the routes in `router.tsx`: fetch `GET /users/me` and redirect non-admins to the dashboard; show an "Admin" sidebar section only when `is_admin`.

**Acceptance criteria:**
- [ ] `GET /api/v1/admin/stats` returns 200 for an admin user with all fields from `AdminStatsResponse`, and 403 for a non-admin, 401 without a token
- [ ] `mrr_estimate_usd` equals (active pro subs × 49) + (active enterprise subs × 499) when using the default `PLANS` prices, verified with seeded subscriptions in a test
- [ ] `GET /api/v1/admin/users?q=alice` returns only users whose email contains "alice" (case-insensitive) with correct `total` and pagination
- [ ] Usage fields in `/admin/stats` equal the sums of the current-period `UsageRecord` rows (seed two workspaces, assert the totals)
- [ ] Frontend: a non-admin visiting `/admin` is redirected away; an admin sees the stats cards populated

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_admin_service.py tests/integration/api/test_admin.py -v` (create both files)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run build && npm run lint`
- [ ] Manual check: set `is_admin=true` on a dev user in the DB, log in, open the Admin sidebar section, and see live counts matching `SELECT count(*)` queries

**Dependencies:** T40

**Files likely touched:**
- `backend/app/api/deps.py`
- `backend/app/schemas/admin.py`
- `backend/app/services/admin_service.py`
- `backend/app/api/v1/endpoints/admin.py`
- `backend/app/api/v1/router.py`
- `backend/tests/unit/services/test_admin_service.py`
- `backend/tests/integration/api/test_admin.py`
- `frontend/src/features/settings/admin/AdminDashboardPage.tsx`
- `frontend/src/features/settings/admin/AdminUsersPage.tsx`
- `frontend/src/features/settings/admin/AdminWorkspacesPage.tsx`
- `frontend/src/router.tsx`
- `frontend/src/components/layout/Sidebar.tsx`

**Estimated scope:** M
