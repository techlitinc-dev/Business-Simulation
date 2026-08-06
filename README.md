# The Forge — AI-Powered Business Simulation SaaS

A digital wind tunnel for entrepreneurs: build a business blueprint, simulate
24+ months of operations on a deterministic financial engine, get stress-tested
by LLM-generated hurdles, make branching strategic decisions in a War Room, and
receive Monte-Carlo-driven resilience audits with prescriptive optimizations.

Two brains:

- **Deterministic Engine** (pure Python): cash, payroll, churn, demand,
  LTV/CAC — physics that cannot be overridden.
- **AI Cortex** (cheap LLM via any OpenAI-compatible API): narrative hurdles,
  strategic options, post-mortems — meaning layered on top of the engine's math.

## Quick start (<15 minutes)

```bash
cp .env.example .env
docker compose up -d
make migrate
make seed
```

Then open **http://localhost:5173** and log in as the demo user:

- **Email:** `demo@forge.dev`
- **Password:** `demo-password-123`

You'll see the "Demo Ventures" workspace with 3 sample blueprints, a completed
baseline run with tick data on the dashboard, and 3 marketplace scenarios.

> `make seed` is idempotent — safe to run as many times as you like.

## What's where

| URL | Purpose |
|---|---|
| `http://localhost:5173` | Frontend app |
| `http://localhost:8000/health` | Liveness probe |
| `http://localhost:8000/ready` | Readiness probe (DB + Redis) |
| `http://localhost:8000/metrics` | Prometheus metrics |
| `http://localhost:8000/docs` | OpenAPI docs |

## Development

```bash
make lint-backend    # ruff + mypy
make test-backend    # pytest (engine ≥90%, API integration ≥70% coverage gates)
make lint-frontend   # eslint
make build-frontend  # tsc + vite build
make migrate         # alembic upgrade head
make seed            # idempotent demo data
```

Backend tests live in `backend/tests/` — unit (engine/agents/services) and
integration (FastAPI via httpx against a sqlite test DB). No network, no real
LLM, no real Stripe: the deterministic mock provider and mocked Stripe keep the
suite hermetic.

## LLM providers

No API key? Everything still works via a deterministic mock provider. With a
key, point `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY` at DeepSeek, OpenAI, or a
local Ollama — see `docs/llm-providers.md` for copy-paste env blocks.

## Documentation

- `docs/api.md` — full v1 API reference (generated from the actual routers)
- `docs/deployment.md` — env vars, migrations, seeding, backups, runbook
- `docs/llm-providers.md` — provider setup
- `tasks/` — implementation plan and per-phase task cards

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs backend lint + mypy + tests +
coverage gates and frontend lint + build on push/PR to `main`.

## Layout

- `backend/` — FastAPI app, engine, agents, workers, alembic migrations
- `frontend/` — React 18 + Vite + Tailwind + shadcn/ui
- `tasks/` — implementation plan and per-phase task cards
