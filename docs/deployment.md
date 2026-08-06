# Deployment

Single-host deployment of The Forge: Postgres + Redis + backend + worker +
nginx-frontend, all via Docker Compose. See the **Production Deploy Runbook**
section at the bottom (written in T51) for the full production procedure.

## Environment variables

All settings live in `.env` (copy from `.env.example`). Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://forge:forge@db:5432/forge` | Postgres DSN |
| `REDIS_URL` | `redis://redis:6379/0` | Redis (Celery broker + live-run state) |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT signing — **set a strong value** |
| `FRONTEND_URL` | `http://localhost:5173` | Public frontend origin |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | DeepSeek / empty / deepseek-chat | AI Cortex provider (see `docs/llm-providers.md`) |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | empty | Stripe billing |
| `STRIPE_PRICE_PRO_MONTHLY` / `STRIPE_PRICE_ENTERPRISE_MONTHLY` | empty | Stripe price IDs |
| `SENTRY_DSN` / `SENTRY_TRACES_SAMPLE_RATE` | empty / 0.0 | Error tracking (T48) |
| `ENVIRONMENT` | `development` | `production` enables HSTS + prod CORS |
| `CORS_ORIGINS` | localhost:5173 | Comma-separated allowed origins (T49) |
| `RATE_LIMIT_DEFAULT` / `RATE_LIMIT_AUTH` / `RATE_LIMIT_REGISTER` | 100/10/20 per minute | Global + auth route limits (T49) |
| `REPORT_STORAGE_DIR` | `./var/reports` | Where exported PDFs are written |

## Migrations

```bash
make migrate   # docker compose exec backend alembic upgrade head
```

Alembic migrations live in `backend/alembic/versions/`; the chain is
linear and round-trips cleanly (`upgrade head` / `downgrade -N`).

## Seeding demo data

```bash
make seed   # docker compose exec backend python -m app.utils.seed
```

Idempotent — safe to run repeatedly. Creates:

- demo user `demo@forge.dev` / `demo-password-123` (override via `SEED_DEMO_PASSWORD`)
- workspace "Demo Ventures" (owner: demo user)
- 3 Format A blueprints (SaaSFlow, BrewBox, ConsultPro)
- one completed baseline run with 24 ticks (dashboard isn't empty)
- 3 public marketplace scenarios

## Backups

The production compose includes a `backup` service that dumps Postgres to
`./backups/forge-*.sql.gz` daily and retains 14 days. Restore:

```bash
gunzip -c backups/forge-<timestamp>.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres psql -U forge forge
```

---

# Production Deploy Runbook

Single-host production stack via `docker-compose.prod.yml`. The only host port
published is `80` (nginx/frontend); Postgres and Redis are internal.

## 1. Initial server setup

```bash
# Install Docker Engine + Compose plugin (Debian/Ubuntu example)
curl -fsSL https://get.docker.com | sh

# Clone the repo and prepare env
git clone <your-repo-url> forge && cd forge
cp .env.example .env
```

Set strong secrets in `.env`:

| Variable | Requirement |
|---|---|
| `JWT_SECRET_KEY` | 32+ random bytes — `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | strong unique password |
| `CORS_ORIGINS` | your real frontend domain (e.g. `https://forge.example.com`) |
| `SENTRY_DSN` | your Sentry project DSN (optional) |
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | your AI provider (see `docs/llm-providers.md`) |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` / price IDs | for billing |

## 2. Build & boot

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## 3. Migrate & seed

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python -m app.utils.seed
```

## 4. DNS / TLS

Terminate TLS at your load balancer, or add certbot on the host:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d forge.example.com
```

## 5. Backups & restore

The `backup` service dumps Postgres to `./backups/forge-*.sql.gz` daily and
retains 14 days. Restore a backup:

```bash
gunzip -c backups/forge-<timestamp>.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres psql -U forge forge
```

## 6. Smoke-test checklist

```bash
curl -i localhost/health          # 200 {"status":"ok",...}
curl -i localhost/ready           # 200 {"status":"ready","checks":{"db":"ok","redis":"ok"}}
curl localhost/metrics | head     # Prometheus counters (http_requests_total)
curl -i localhost/                # frontend HTML
```

Then in the browser: log in as `demo@forge.dev` / `demo-password-123` (from
`make seed`), open a blueprint, and start a baseline run — the dashboard cash
curve should animate.

## 7. Updates

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## 8. Troubleshooting

- `backend` unhealthy: check `docker compose -f docker-compose.prod.yml logs backend`
- `alembic` can't reach DB: confirm `postgres` healthcheck is green
  (`docker compose -f docker-compose.prod.yml ps`)
- Rate-limit 429s in normal use: raise `RATE_LIMIT_DEFAULT` / `RATE_LIMIT_AUTH`
- CORS errors in the browser: ensure `CORS_ORIGINS` exactly matches the origin
  users see in the address bar (scheme + host + port)
