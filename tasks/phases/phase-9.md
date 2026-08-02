# Phase 9 — Production Hardening

Final hardening pass: coverage gates in CI, observability (request IDs, Sentry, Prometheus, health/readiness probes), security (rate limits, CORS, headers, audit log), demo seed data + full documentation, and a production deployment story with backups and a runbook.

## Task T47: Test coverage push — engine ≥90%, API integration ≥80%

**Description:** Raise and lock in test coverage so regressions are caught in CI. Add `pytest-cov` (and `coverage[toml]`) to `backend/requirements.txt`. Configure coverage in `backend/pyproject.toml` under `[tool.coverage.run]` / `[tool.coverage.report]` with `show_missing = true` and branch coverage enabled. Write whatever additional tests are needed so that `app/engine/` (financials.py, market.py, loop.py, events.py, metrics.py, state.py) reaches **≥90% line coverage** and the API layer (`app/api/`, exercised via `tests/integration/api/`) reaches **≥80%**. Engine tests must stay pure (no DB/network) and seeded-deterministic: cover every formula in `financials.py` (LTV = price_point × (1 / churn_monthly); LTV:CAC ratio; runway = cash / net_burn; MRR/ARR; NRR), each demand/elasticity/seasonality branch in `market.py`, every trigger in `loop.py` (bankruptcy, profitability, funding-need, milestone), and each event-impact application in `events.py` (cac_delta_percent, churn_delta_percent, new_signups_delta_percent, cash_burn_delta_monthly — the `mechanical_impact.immediate` keys from Format B). Integration tests use httpx `AsyncClient` against the FastAPI app with a test DB and the deterministic mock LLM provider (no `LLM_API_KEY`) — cover every router in `app/api/v1/endpoints/`: auth happy+failure paths, workspace RBAC denials, blueprint CRUD/versioning/validation, simulation start/state/decide, reports, scenarios, billing webhook idempotency (mocked Stripe signature), api-keys, admin. Finally, add a coverage gate step to `.github/workflows/ci.yml` that fails the build below the thresholds.

**Acceptance criteria:**
- [ ] `cd backend && pytest --cov=app/engine --cov-report=term-missing tests/unit/engine` reports ≥90% line coverage for `app/engine/` and exits 0 with `--cov-fail-under=90`
- [ ] `cd backend && pytest --cov=app/api --cov-report=term-missing tests/integration` reports ≥80% line coverage for `app/api/` and exits 0 with `--cov-fail-under=80`
- [ ] Coverage config lives in `backend/pyproject.toml` (not CLI flags only); `--cov-fail-under` thresholds are recorded there or in the CI step
- [ ] `.github/workflows/ci.yml` backend job runs both coverage commands and fails on threshold breach (verified by the step using `--cov-fail-under`)
- [ ] No test requires network, a real LLM API key, or a real Stripe key (mock provider + mocked Stripe everywhere)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/engine tests/integration -v --cov=app --cov-report=term-missing` — new tests go in `backend/tests/unit/engine/` (e.g. `test_financials_edges.py`, `test_market.py`, `test_loop_triggers.py`, `test_events.py`, `test_metrics.py`) and `backend/tests/integration/api/` (one `test_<router>.py` per endpoint module)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: open the `term-missing` output and confirm no `app/engine/*.py` file has uncovered lines in its core formula functions

**Dependencies:** all core phases (T01–T46)

**Files likely touched:**
- `backend/requirements.txt`
- `backend/pyproject.toml`
- `backend/tests/unit/engine/test_financials_edges.py` (new)
- `backend/tests/unit/engine/test_market.py` (new)
- `backend/tests/unit/engine/test_loop_triggers.py` (new)
- `backend/tests/unit/engine/test_events.py` (new)
- `backend/tests/unit/engine/test_metrics.py` (new)
- `backend/tests/integration/api/test_*.py` (new/extended, one per endpoint module)
- `.github/workflows/ci.yml`

**Estimated scope:** L

## Task T48: Observability — request-id logging, Sentry, Prometheus metrics, readiness probes

**Description:** Make the backend operable in production. (1) **Request-ID middleware** in `app/main.py`: an `http` middleware that reads `X-Request-ID` from the incoming request or generates a `uuid4().hex`, binds it into structlog contextvars (from `app/core/logging.py`) so every log line in that request carries `request_id`, and echoes it back as the `X-Request-ID` response header. (2) **Sentry**: add `sentry-sdk[fastapi]` to requirements; in the app factory call `sentry_sdk.init(dsn=settings.SENTRY_DSN, integrations=[FastApiIntegration()], traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE)` **only if `SENTRY_DSN` is non-empty** — with no DSN the app must boot identically. Add `SENTRY_DSN: str = ""` and `SENTRY_TRACES_SAMPLE_RATE: float = 0.0` to `app/core/config.py`. (3) **Prometheus**: add `prometheus-fastapi-instrumentator`; expose `GET /metrics` (not under `/api/v1`, unauthenticated, standard `request_count`/`request_latency` metrics, grouped by handler+method+status). (4) **Probes**: keep existing `GET /health` as a pure liveness check (always 200 `{"status": "ok"}` when the process is up); add `GET /ready` in the same module that runs `SELECT 1` through the async SQLAlchemy session (`app/db/session.py`) and `PING` against Redis (the same client used by workers), returning `200 {"status": "ready", "checks": {"db": "ok", "redis": "ok"}}` or `503` with the failing check named. Add a test raising/verifying both paths.

**Acceptance criteria:**
- [ ] Every response carries an `X-Request-ID` header; a client-supplied `X-Request-ID` is preserved verbatim
- [ ] App boots and all tests pass with `SENTRY_DSN` unset; when a DSN is set, `sentry_sdk.init` is called (verified by monkeypatching in a unit test)
- [ ] `GET /metrics` returns Prometheus text format containing `http_requests_total`
- [ ] `GET /ready` returns 200 when DB+Redis are reachable and 503 with the failing component named when either check raises (both paths tested)
- [ ] `/metrics`, `/health`, `/ready` are not rate-limited and not under `/api/v1`

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/api/test_health.py tests/unit/test_observability.py -v` (create both files; use httpx `AsyncClient` + monkeypatched session/Redis for the failure paths)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `docker compose up -d && curl -i localhost:8000/ready` shows `X-Request-ID` in headers and `checks.db: ok` in the body; `curl localhost:8000/metrics | head` shows Prometheus counters

**Dependencies:** T02

**Files likely touched:**
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/logging.py`
- `backend/app/api/v1/endpoints/` health routes (or new `backend/app/api/health.py` registered outside v1)
- `backend/requirements.txt`
- `backend/tests/integration/api/test_health.py` (new)
- `backend/tests/unit/test_observability.py` (new)
- `.env.example`

**Estimated scope:** M

## Task T49: Security hardening — rate limits, CORS, security headers, audit log

**Description:** Close the common web-attack surface and make privileged actions auditable. (1) **Global rate limits**: extend the slowapi `Limiter` in `app/core/rate_limit.py` (keyed by `get_remote_address`) with a global default of `"100/minute"` applied via a middleware or `default_limits`, plus stricter per-route limits on credential endpoints: `POST /api/v1/auth/login` and `/forgot-password` at `"10/minute"`, `/register` at `"20/minute"`. Exceeding the limit returns 429 with body `{"detail": "rate limit exceeded"}`. Limits are configurable via settings (`RATE_LIMIT_DEFAULT`, `RATE_LIMIT_AUTH`) and disabled in the test environment (`TESTING=true`) except in the dedicated rate-limit tests that override the limiter. (2) **Strict CORS**: `CORSMiddleware` in `app/main.py` with `allow_origins=settings.CORS_ORIGINS` (a `list[str]` from env, e.g. `["http://localhost:5173"]` in dev, the production domain in prod — never `["*"]`), `allow_credentials=True`, explicit `allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"]` and `allow_headers=["Authorization","Content-Type","X-Request-ID"]`. (3) **Security headers middleware**: add a middleware setting `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy: default-src 'self'`, and `Strict-Transport-Security: max-age=31536000; includeSubDomains` only when `settings.ENVIRONMENT == "production"`. (4) **Audit log**: new SQLAlchemy model + Alembic migration `audit_log` with columns `id`, `created_at`, `request_id`, `user_id` (nullable FK), `workspace_id` (nullable), `method`, `path`, `status_code`, `ip_address`, `user_agent`, and an `AuditLogMiddleware` that records every mutating request (`POST`/`PUT`/`PATCH`/`DELETE`) under `/api/v1/` asynchronously after the response (write via an independent async session so it never breaks the request; skip `/metrics`, `/health`, `/ready`, and WebSocket upgrades). Retrieval stays admin-only: extend `app/api/v1/endpoints/admin.py` with `GET /api/v1/admin/audit-log?user_id=&path=&limit=` requiring the existing admin guard.

**Acceptance criteria:**
- [ ] 11 rapid `POST /api/v1/auth/login` calls from one IP return a 429 with the documented body (with test-mode limiter configured to a low limit)
- [ ] A preflight `OPTIONS` from an origin not in `CORS_ORIGINS` receives no `Access-Control-Allow-Origin`; an allowed origin does
- [ ] All responses include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP; `Strict-Transport-Security` appears only with `ENVIRONMENT=production`
- [ ] A `POST` (e.g. creating a blueprint) produces exactly one `audit_log` row with matching `method`, `path`, `status_code`, `user_id`, and the request's `X-Request-ID`
- [ ] `GET /api/v1/admin/audit-log` returns 200 for an admin and 403 for a non-admin; failed audit writes are logged but never change the response status

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/api/test_security.py tests/integration/api/test_audit_log.py -v` (create both files; override limiter limits per-test, use the test DB to assert `audit_log` rows)
- [ ] Migration applies cleanly: `cd backend && alembic upgrade head`
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `curl -si -X POST localhost:8000/api/v1/auth/login` (11+ times) ends in 429; response headers show the four security headers

**Dependencies:** T45

**Files likely touched:**
- `backend/app/core/rate_limit.py`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/models/audit_log.py` (new)
- `backend/alembic/versions/<new_revision>_audit_log.py` (new)
- `backend/app/api/v1/endpoints/admin.py`
- `backend/tests/integration/api/test_security.py` (new)
- `backend/tests/integration/api/test_audit_log.py` (new)
- `.env.example`

**Estimated scope:** M

## Task T50: Seed data + demo content + documentation (README, docs/api.md, docs/deployment.md, docs/llm-providers.md)

**Description:** Give a new developer (and a sales demo) a working system in minutes. (1) **Seed script** `backend/app/utils/seed.py` exposing `async def seed(session) -> None`, wired to a `make seed` Makefile target (`docker compose exec backend python -m app.utils.seed`). It must be **idempotent** (check-then-insert on email/slug/title). It creates: demo user `demo@forge.dev` / password `demo-password-123` (documented, overridable via `SEED_DEMO_PASSWORD` env), a workspace "Demo Ventures" with the demo user as owner, and **3 realistic blueprints** whose `payload` strictly follows spec Format A (§10) — each with full `business_profile`, `revenue_engine.streams[]` (price_point, ltv, cac, churn_monthly), `cost_structure` (fixed_monthly, team[], burn_rate_month_1), `financials` (starting_capital, target_runway_months), and `simulation_parameters`. Suggested archetypes: "SaaSFlow — B2B Productivity SaaS" (the §10 Format A example: $99/mo, LTV 2400, CAC 850, 5% churn, $500k capital), "BrewBox — DTC Coffee Subscription" (Subscription, $29 price, higher churn 0.08, lower capital $120k), "ConsultPro — Boutique Agency" (Project pricing_model, lumpy revenue, 3-person team, $80k capital). For the first blueprint also seed one completed baseline `SimulationRun` (status=`completed`, seed=42, populated `result` JSONB + a few `TickLog` rows) so the dashboard isn't empty. Plus **3 public marketplace scenarios** (`is_public=True`, authored by the demo workspace): "Freemium Assault" (a competitor-launches-free-tier scenario embedding the §10 Format B hurdle), "Key Engineer Quits" (talent category), "Series A Winter" (funding category, investor pullback). (2) **Docs**: rewrite `README.md` with a <15-minute quickstart (`cp .env.example .env` → `docker compose up -d` → `make migrate && make seed` → login as demo user); write `docs/api.md` documenting every v1 route from `plan.md` (method, path, auth, request/response schema names, status codes — generated from the actual routers, not aspirational); `docs/deployment.md` covering env vars table, migration/seed commands, and pointing to the T51 runbook section; `docs/llm-providers.md` with copy-paste env blocks for DeepSeek (`LLM_BASE_URL=https://api.deepseek.com/v1`, `LLM_MODEL=deepseek-chat`), OpenAI (`LLM_BASE_URL=https://api.openai.com/v1`, `LLM_MODEL=gpt-4o-mini`), and Ollama (`LLM_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=llama3.1`, any placeholder `LLM_API_KEY=ollama`), plus a paragraph explaining the mock-provider fallback when no key is set.

**Acceptance criteria:**
- [ ] Running `make seed` twice produces no duplicates and no errors (idempotent)
- [ ] After seeding, logging in as `demo@forge.dev` shows workspace "Demo Ventures", 3 blueprints (each passing the existing blueprint validation service), and one completed simulation run with tick data
- [ ] `GET /api/v1/scenarios/featured` (or the public browse endpoint) returns the 3 seeded scenarios
- [ ] Every seeded blueprint payload validates against the Format A Pydantic schema from T16 (asserted by a test calling `seed()` against the test DB)
- [ ] `README.md` quickstart has ≤6 commands and ends with the demo login credentials; `docs/llm-providers.md` contains working env blocks for DeepSeek, OpenAI, and Ollama

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/test_seed.py -v` (create this file: run `seed()` on the test DB twice, assert counts and Format A schema validity of all payloads)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: fresh `docker compose up -d && make migrate && make seed`, log in via the frontend as `demo@forge.dev`, and confirm dashboard + marketplace show seeded content

**Dependencies:** T42

**Files likely touched:**
- `backend/app/utils/seed.py` (new)
- `backend/tests/integration/test_seed.py` (new)
- `Makefile`
- `README.md`
- `docs/api.md` (new)
- `docs/deployment.md` (new)
- `docs/llm-providers.md` (new)
- `.env.example`

**Estimated scope:** M

## Task T51: Production deployment — prod Dockerfiles, docker-compose.prod.yml, DB backups, deploy runbook

**Description:** Produce a single-host production deployment. (1) **Multi-stage `backend/Dockerfile`**: builder stage installs `requirements.txt` into a venv on `python:3.12-slim`; runtime stage copies only the venv + `app/` + `alembic/`, creates a non-root user, and runs `gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 app.main:app` (add `gunicorn` to requirements). Keep the dev compose overriding the command with `uvicorn --reload`. (2) **Multi-stage `frontend/Dockerfile`**: stage 1 `node:20-alpine` runs `npm ci && npm run build`; stage 2 `nginx:alpine` serves `dist/` via a new `frontend/nginx.conf` that serves static assets and reverse-proxies `/api/`, `/metrics`, `/health`, `/ready` to `backend:8000` and `/ws/` with the WebSocket upgrade headers (`proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`). (3) **`docker-compose.prod.yml`**: services `postgres` (named volume `pgdata`, no host port), `redis` (named volume, no host port), `backend` (depends_on healthy postgres+redis, env from `.env`, `ENVIRONMENT=production`), `worker` (same image, celery command), `frontend` (the only published port, `80:80`), and `backup` — a `postgres:16-alpine` container running a cron-style `sh -c` loop (`while true; do pg_dump ... | gzip > /backups/forge-$(date +%Y%m%d-%H%M).sql.gz; sleep 86400; done`) writing to a `./backups` bind mount, with retention (`find /backups -name '*.sql.gz' -mtime +14 -delete`). (4) **Runbook**: append a "Production Deploy Runbook" section to `docs/deployment.md` covering: initial server setup (install docker, copy `.env`, set strong `SECRET_KEY`/DB passwords, set `CORS_ORIGINS` and `SENTRY_DSN`), `docker compose -f docker-compose.prod.yml up -d --build`, running `alembic upgrade head` + seed, DNS/TLS note (terminate TLS at your LB or add certbot), restore procedure (`gunzip -c backup.sql.gz | docker compose exec -T postgres psql -U forge forge`), and a smoke-test checklist (`/health`, `/ready`, `/metrics`, login as demo user, start a baseline run).

**Acceptance criteria:**
- [ ] `docker compose -f docker-compose.prod.yml build` succeeds for all services; backend and frontend images each use multi-stage builds (runtime stage has no build tooling; backend runs as non-root — verify `docker compose -f docker-compose.prod.yml exec backend whoami` is not `root`)
- [ ] `docker compose -f docker-compose.prod.yml up -d` boots the stack; `curl localhost/health` and `curl localhost/ready` return 200 through nginx, and the frontend HTML loads at `http://localhost/`
- [ ] Only the frontend/nginx port is published to the host (postgres and redis have no `ports:` mapping in `docker-compose.prod.yml`)
- [ ] Triggering the backup loop once (e.g. `docker compose -f docker-compose.prod.yml exec backup sh -c 'pg_dump ...'`) produces a non-empty `.sql.gz` in `./backups/` and the documented restore command round-trips
- [ ] `docs/deployment.md` contains the runbook section with deploy, migrate, backup-restore, and smoke-test steps

**Verification:**
- [ ] Tests pass: `cd backend && pytest` (full suite still green — this task adds no app-code behavior) and `cd frontend && npm run build`
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run lint`
- [ ] Manual check: from a clean checkout, `docker compose -f docker-compose.prod.yml up -d --build`, then run every command in the runbook's smoke-test checklist and observe each expected result

**Dependencies:** T48, T49

**Files likely touched:**
- `backend/Dockerfile`
- `backend/requirements.txt`
- `frontend/Dockerfile`
- `frontend/nginx.conf` (new)
- `docker-compose.prod.yml`
- `docs/deployment.md`
- `.env.example`

**Estimated scope:** M

## Checkpoint E (after T51)

- [ ] Staging deploy passes smoke tests: `docker compose -f docker-compose.prod.yml up -d` → `/health`, `/ready`, `/metrics` all 200; demo user can log in and start a baseline run end-to-end
- [ ] A new dev can run the full stack from `README.md` in <15 minutes (quickstart: `cp .env.example .env` → `docker compose up -d` → `make migrate && make seed` → login)
- [ ] CI enforces lint + tests + coverage gates (engine ≥90%, API integration ≥80%) — a failing threshold blocks merge
