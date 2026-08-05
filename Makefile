.PHONY: up down logs test-backend lint-backend build-frontend lint-frontend migrate

# Bring up the full dev stack (db, redis, backend, worker, frontend)
up:
	docker compose up -d --build

# Tear the stack down
down:
	docker compose down

# Tail logs for all services
logs:
	docker compose logs -f

# Backend
test-backend:
	cd backend && pytest

lint-backend:
	cd backend && ruff check app tests && mypy app

# Frontend
build-frontend:
	cd frontend && npm run build

lint-frontend:
	cd frontend && npm run lint

# Database migrations
migrate:
	docker compose exec backend alembic upgrade head
