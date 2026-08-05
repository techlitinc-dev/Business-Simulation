# The Forge — AI-Powered Business Simulation SaaS

A digital wind tunnel for entrepreneurs: build a business blueprint, simulate 24+
months of operations on a deterministic financial engine, get stress-tested by
LLM-generated hurdles, and receive Monte-Carlo-driven resilience audits.

Two brains:
- **Deterministic Engine** (pure Python): cash, payroll, churn, demand, LTV/CAC.
- **AI Cortex** (cheap LLM via OpenAI-compatible API): narrative hurdles,
  strategic options, post-mortems — meaning layered on top of the engine's math.

## Quick start

```bash
cp .env.example .env
make up
```

- Backend API: http://localhost:8000 (`/health`)
- Frontend: http://localhost:5173

## Development

```bash
make lint-backend    # ruff + mypy
make test-backend    # pytest
make lint-frontend   # eslint
make build-frontend  # tsc + vite build
make migrate         # alembic upgrade head
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs backend lint+test and frontend
lint+build on push/PR to `main`. Branch protection should require the `backend`
and `frontend` jobs to pass before merging.

## Layout

- `backend/` — FastAPI app, engine, agents, workers
- `frontend/` — React 18 + Vite + Tailwind + shadcn/ui
- `tasks/` — implementation plan and per-phase task cards
