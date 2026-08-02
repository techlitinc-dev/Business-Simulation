# Phase 0 — Scaffolding & DevOps

Monorepo skeleton, backend/frontend scaffolds, async DB layer, and CI so every later task has a runnable, lintable, testable baseline.

## Task T01: Monorepo skeleton, `.env.example`, Makefile, docker-compose (postgres, redis, backend, worker, frontend)

**Description:** Create the repo-level scaffolding for the monorepo defined in `tasks/plan.md`: empty `backend/` and `frontend/` directory trees (with `.gitkeep` files where needed), a root `.gitignore` (Python: `__pycache__`, `.venv`, `.env`, `*.egg-info`; Node: `node_modules`, `dist`; OS: `.DS_Store`), a root `.env.example` documenting every env var the system will read, a root `Makefile` with dev/test/lint targets, and a root `docker-compose.yml` with five services: `db` (postgres:16-alpine), `redis` (redis:7-alpine), `backend` (build `./backend`, port 8000, runs uvicorn with `--reload`, mounts `./backend` as a volume, depends on db+redis healthchecks), `worker` (same build as backend, command `celery -A app.workers.celery_app worker --loglevel=info`, depends on redis; until T02 creates `app/workers/celery_app.py` this service may stay with `profiles: ["full"]` or a trivial command — decide so `docker compose up` succeeds after T02), and `frontend` (build `./frontend`, port 5173). `.env.example` must include (with safe dummy values):

```
DATABASE_URL=postgresql+asyncpg://forge:forge@db:5432/forge
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=change-me-in-production
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=
LLM_MODEL=deepseek-chat
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
SMTP_HOST=
SMTP_FROM=noreply@forge.local
```

Compose services must read config from these env vars (via `env_file: .env` on backend/worker) and must not hardcode credentials anywhere else. Also create a minimal root `README.md` (≤30 lines: what the project is, `cp .env.example .env && make up`).

**Acceptance criteria:**
- [ ] Root contains `.env.example`, `.gitignore`, `Makefile`, `docker-compose.yml`, `README.md`, `backend/`, `frontend/`
- [ ] `Makefile` defines exactly these targets: `up` (docker compose up -d --build), `down`, `logs`, `test-backend` (cd backend && pytest), `lint-backend` (cd backend && ruff check app tests && mypy app), `build-frontend` (cd frontend && npm run build), `lint-frontend` (cd frontend && npm run lint), `migrate` (docker compose exec backend alembic upgrade head)
- [ ] `docker compose config` validates with no errors
- [ ] `db` and `redis` services have healthchecks (`pg_isready`, `redis-cli ping`); `backend` and `worker` use `depends_on: condition: service_healthy`
- [ ] No real credentials committed; `.env` is in `.gitignore`

**Verification:**
- [ ] Lint/build passes: `docker compose config --quiet`
- [ ] Manual check: `cp .env.example .env && docker compose up -d db redis && docker compose ps` shows `db` and `redis` healthy

**Dependencies:** None

**Files likely touched:**
- `.env.example`
- `.gitignore`
- `Makefile`
- `docker-compose.yml`
- `README.md`

**Estimated scope:** M

## Task T02: Backend scaffold: FastAPI app factory, pydantic-settings, structlog, `/health`, exception handlers

**Description:** Create the Python 3.12 FastAPI backend skeleton under `backend/`. Use an **app factory**: `app/main.py` exposes `create_app() -> FastAPI` (and a module-level `app = create_app()` for uvicorn) that wires middleware, routers, and exception handlers. `app/core/config.py` defines a `Settings` class with **pydantic-settings v2** (`BaseSettings`, `model_config = SettingsConfigDict(env_file=".env")`) with fields: `database_url`, `redis_url`, `jwt_secret_key`, `llm_base_url`, `llm_api_key` (Optional, empty string allowed — the deterministic mock provider in later phases is used when it is unset), `llm_model`, `stripe_secret_key` (Optional), `stripe_webhook_secret` (Optional), `smtp_host` (Optional), `smtp_from`, plus `debug: bool = False`; expose a cached `get_settings()`. `app/core/logging.py` configures **structlog** (JSON renderer when `debug=False`, pretty console renderer when `debug=True`) with a `setup_logging()` called from `create_app()`. `app/core/exceptions.py` defines `DomainError(Exception)` with `status_code: int` and `detail: str` attributes, and registers handlers in `create_app()`: one for `DomainError` and one catch-all for `Exception` (500, logs via structlog, never leaks the traceback to the client); both return `{"detail": <message>}`. Add `GET /health` (no prefix) returning 200 `{"status": "ok", "version": <settings-derived app version string, e.g. "0.1.0">}`, and `GET /api/v1/health` on the v1 router returning the same body. Create `app/api/v1/router.py` with an `APIRouter(prefix="/api/v1")` placeholder and `app/api/deps.py` with a stub `get_db` (real implementation in T04) — keep imports working. Create a minimal `app/workers/celery_app.py` (Celery instance named `"forge"`, broker/backend from `settings.redis_url`, one no-op task `ping()`) so the compose `worker` service starts. Write `backend/requirements.txt` pinning compatible versions: `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings>=2`, `structlog`, `sqlalchemy[asyncio]>=2.0`, `alembic`, `asyncpg`, `celery[redis]`, `redis`, plus dev deps `pytest`, `pytest-asyncio`, `httpx`, `aiosqlite`, `ruff`, `mypy`. Write `backend/pyproject.toml` with tool config: ruff (target `py312`, line-length 100, select `E,F,I,UP,B`), mypy (python_version 3.12, `strict = true` relaxed only with explicit per-module overrides for third-party libs missing stubs), pytest (`asyncio_mode = "auto"`, testpaths `tests`). Write `backend/Dockerfile` (python:3.12-slim, install requirements, `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`; compose overrides with `--reload`). Create `tests/conftest.py` (httpx `AsyncClient` fixture with `ASGITransport` bound to `create_app()`) and `tests/integration/api/test_health.py`.

**Acceptance criteria:**
- [ ] `create_app()` returns a FastAPI instance; `uvicorn app.main:app` boots without a DB or any env vars beyond defaults in `.env.example`
- [ ] `GET /health` returns 200 with JSON `{"status": "ok", "version": "..."}`; `GET /api/v1/health` returns the same
- [ ] `Settings` loads from env vars and from `.env` when present; `llm_api_key` may be empty without error
- [ ] Raising `DomainError(status_code=422, detail="x")` in a handler yields 422 `{"detail": "x"}`; an unexpected exception yields 500 `{"detail": "Internal server error"}` and is logged via structlog
- [ ] structlog emits one JSON log line per request to stdout when `debug=False`
- [ ] `celery -A app.workers.celery_app inspect ping` succeeds against the compose redis

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/api/test_health.py -v` — create `tests/integration/api/test_health.py` asserting both health routes return 200 and the exact body shape, and `tests/unit/test_exceptions.py` asserting the `DomainError` and catch-all handler behavior via httpx against a tiny test app with a route that raises each
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `docker compose up -d --build backend && curl localhost:8000/health` prints `{"status":"ok","version":"0.1.0"}`

**Dependencies:** T01

**Files likely touched:**
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/logging.py`
- `backend/app/core/exceptions.py`
- `backend/app/api/deps.py`
- `backend/app/api/v1/router.py`
- `backend/app/workers/celery_app.py`
- `backend/requirements.txt`
- `backend/pyproject.toml`
- `backend/Dockerfile`
- `backend/tests/conftest.py`
- `backend/tests/integration/api/test_health.py`
- `backend/tests/unit/test_exceptions.py`

**Estimated scope:** M

## Task T03: Frontend scaffold: Vite+React+TS, Tailwind, shadcn/ui, router, dark theme AppShell

**Description:** Scaffold the frontend under `frontend/` with **Vite + React 18 + TypeScript** (`npm create vite@latest frontend -- --template react-ts`, then adapt to the plan's tree). Add **Tailwind CSS v3.4** (v3, not v4 — shadcn/ui's init flow and `tailwind.config.ts` token setup are stable on v3; pin `tailwindcss@^3.4`) with `tailwind.config.ts` and `src/styles/index.css` (tailwind directives + CSS variables for the dark theme tokens). Initialize **shadcn/ui** (components.json with style `default`, base color `slate`, CSS variables enabled, alias `@/` → `src/`; configure the `@` path alias in both `tsconfig.json` and `vite.config.ts`) and generate at least the `button` primitive at `src/components/ui/button.tsx` via `npx shadcn@latest add button`. Install **react-router-dom v6**, **@tanstack/react-query**, and **zustand** (both will be used by later tasks; wire `QueryClientProvider` with a default `QueryClient` in `src/main.tsx` now). Create `src/router.tsx` exporting a `createBrowserRouter` router with routes: `/` → marketing placeholder, `/login` → placeholder, `/app` → AppShell layout with a dashboard placeholder child route; `src/App.tsx` renders `<RouterProvider>`. Create `src/components/layout/AppShell.tsx`, `Sidebar.tsx`, `Topbar.tsx`: a dark-first shell (set `class="dark"` on `<html>` in `index.html` or via a useEffect in App) with a fixed left sidebar (app name "The Forge", nav links: Dashboard, Blueprints, Simulations, Reports, Settings — only Dashboard needs a working route; others may render a "Coming soon" placeholder page), a top bar with workspace name placeholder and a user avatar placeholder, and an `<Outlet />` content area. Add `src/lib/utils.ts` (the shadcn `cn()` helper), `src/lib/constants.ts` (app name, nav items), and a stub `src/lib/api-client.ts` (typed fetch wrapper reading base URL from `import.meta.env.VITE_API_URL` defaulting to `http://localhost:8000` — full auth interceptors come in T07). Ensure `npm run lint` (eslint flat config from the Vite template) and `npm run build` (tsc + vite build) both pass, and write `frontend/Dockerfile` (node:20-alpine build stage → nginx:alpine serving `dist`, or plain dev-server CMD for now — but it must run under compose on port 5173).

**Acceptance criteria:**
- [ ] `cd frontend && npm ci && npm run build` succeeds with zero TypeScript errors
- [ ] `cd frontend && npm run lint` passes
- [ ] Page renders with dark theme by default (background near-black, light text) without any user toggle
- [ ] `/app` renders AppShell with sidebar (5 nav items), topbar, and dashboard placeholder; unknown routes under `/app` show a not-found/coming-soon state instead of a blank screen
- [ ] `src/components/ui/button.tsx` exists and is used at least once in the shell or placeholder page
- [ ] `@/` import alias works in both source and build

**Verification:**
- [ ] Lint/build passes: `cd frontend && npm run lint && npm run build`
- [ ] Manual check: `cd frontend && npm run dev`, open `http://localhost:5173/app` — dark shell with sidebar + topbar renders, no console errors

**Dependencies:** T01

**Files likely touched:**
- `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tailwind.config.ts`, `frontend/components.json`, `frontend/index.html`, `frontend/postcss.config.js`
- `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/router.tsx`
- `frontend/src/styles/index.css`
- `frontend/src/components/layout/AppShell.tsx`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/layout/Topbar.tsx`
- `frontend/src/components/ui/button.tsx`
- `frontend/src/lib/utils.ts`, `frontend/src/lib/constants.ts`, `frontend/src/lib/api-client.ts`
- `frontend/Dockerfile`

**Estimated scope:** M

## Task T04: Database layer: async SQLAlchemy session, base model, Alembic init + first migration

**Description:** Build the async database layer with **SQLAlchemy 2.0 (async)** and **Alembic**. `backend/app/db/base.py` defines `Base(DeclarativeBase)` and a `TimestampMixin` (or common columns on `Base`) providing `id: Mapped[uuid.UUID]` (server/client-generated UUID v4 primary key) plus `created_at` / `updated_at` (`Mapped[datetime]`, timezone-aware, `server_default=func.now()`, `onupdate=func.now()`). `backend/app/db/session.py` creates `async_engine = create_async_engine(settings.database_url, pool_pre_ping=True)` and `async_session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)`, plus the FastAPI dependency `async def get_db() -> AsyncGenerator[AsyncSession, None]` in `app/api/deps.py` (replace the T02 stub) that yields a session from the factory. Initialize Alembic with async support: `cd backend && alembic init alembic`, then rewrite `alembic/env.py` to load `settings.database_url` from `app.core.config` (via a fresh `create_async_engine`, `run_sync` migrations) and set `target_metadata = Base.metadata`; make `alembic.ini`'s `script_location` correct relative to `backend/`. Import all model modules in `env.py` via a single `app.db.base` import hook (there are no models yet — add a comment noting that future model modules must be imported there, or create an empty `app/models/__init__.py` that later tasks extend). Generate the first revision: `alembic revision -m "initial"` — an **empty migration** (no tables exist yet) that still exercises the full upgrade/downgrade path. Tests must run without Postgres: add `tests/integration/test_db.py` using an `aiosqlite`-backed engine to verify `get_db` yields a working `AsyncSession` (e.g. `SELECT 1`) and that `Base.metadata` imports cleanly. Keep `app/engine/` untouched — the engine never imports anything from `app/db/`.

**Acceptance criteria:**
- [ ] `app/db/base.py` defines `Base(DeclarativeBase)` with UUID `id`, `created_at`, `updated_at` available to all future models
- [ ] `get_db` dependency yields an `AsyncSession` and closes it after the request
- [ ] `docker compose exec backend alembic upgrade head` and `alembic downgrade base` both succeed against the compose Postgres with the initial (empty) revision
- [ ] `alembic/env.py` reads the URL from app settings, not from a hardcoded value in `alembic.ini`
- [ ] DB tests pass without a running Postgres (sqlite via aiosqlite)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/test_db.py -v` — create `tests/integration/test_db.py` (aiosqlite session smoke test + metadata import test); full suite: `cd backend && pytest`
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `docker compose up -d db backend && docker compose exec backend alembic upgrade head && docker compose exec backend alembic current` shows the initial revision id

**Dependencies:** T02

**Files likely touched:**
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/api/deps.py`
- `backend/app/models/__init__.py`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/<rev>_initial.py`
- `backend/tests/integration/test_db.py`

**Estimated scope:** M

## Task T05: CI: GitHub Actions workflow (backend lint+test, frontend lint+build)

**Description:** Create `.github/workflows/ci.yml` with two jobs running on `push` and `pull_request` to `main`. Job `backend`: `actions/setup-python@v5` with `python-version: "3.12"` and pip cache keyed on `backend/requirements.txt`; steps: `pip install -r backend/requirements.txt`, `cd backend && ruff check app tests`, `cd backend && mypy app`, `cd backend && pytest` (no services needed — Phase 0 tests use httpx/ASGITransport and aiosqlite, per T02/T04). Job `frontend`: `actions/setup-node@v4` with `node-version: "20"` and npm cache for `frontend/package-lock.json`; steps: `cd frontend && npm ci`, `npm run lint`, `npm run build`. Set `defaults.run.working-directory` per job instead of manual `cd` where cleaner, and give the workflow `concurrency` so pushes to the same PR cancel stale runs. Both jobs must be required-passing (mention in the README that branch protection should require them — do not attempt to configure it from the card).

**Acceptance criteria:**
- [ ] `.github/workflows/ci.yml` exists, valid YAML, triggers on push/PR to `main`
- [ ] Backend job runs exactly: install → `ruff check app tests` → `mypy app` → `pytest`, on Python 3.12 with pip cache
- [ ] Frontend job runs exactly: `npm ci` → `npm run lint` → `npm run build`, on Node 20 with npm cache
- [ ] A test PR/push shows both jobs green (or, without GitHub access, `actionlint` or `python -c "import yaml; yaml.safe_load(...)"` validates the file locally)

**Verification:**
- [ ] Tests pass: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` (YAML validity) — and, if the repo is pushed, the GitHub Actions run for the push is green
- [ ] Lint/build passes: locally re-run the exact CI commands: `cd backend && ruff check app tests && mypy app && pytest` and `cd frontend && npm ci && npm run lint && npm run build`
- [ ] Manual check: Actions tab shows the `ci` workflow with `backend` and `frontend` jobs both green on `main`

**Dependencies:** T02, T03

**Files likely touched:**
- `.github/workflows/ci.yml`
- `README.md` (CI badge / branch-protection note, optional)

**Estimated scope:** S

## Checkpoint

### Checkpoint A (after T05)
- [ ] `docker compose up` boots all services; `GET /health` → 200; frontend renders AppShell; CI green on main
