# connexity Makefile
# Two modes: local (no Docker for app, just DB) and docker (everything in Docker)

.PHONY: help install dev dashboard db db-upgrade db-migrate db-downgrade db-stop \
        docker-up docker-down docker-logs docker-build-up docker-build-down \
        cli lint format test generate-client

# ──────────────────────────────────────────────
# Help
# ──────────────────────────────────────────────

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────
# Local development (app runs natively, DB in Docker)
# ──────────────────────────────────────────────

install: ## Install Python and frontend dependencies
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")
	cd backend && uv venv && uv sync
	cd frontend && pnpm install

dev: ## Start FastAPI backend (local, requires DB running)
	cd backend && uv run uvicorn app.main:app --reload

dashboard: ## Start Next.js dev server (loads repo root .env)
	@test -f .env || (echo "Missing .env; copy .env.example to .env first." >&2 && exit 1)
	set -a && . ./.env && set +a && cd frontend && pnpm dev

db: ## Start Postgres + Adminer in Docker
	docker compose up -d database adminer

db-upgrade: ## Run Alembic migrations to latest
	cd backend && uv run python -m alembic upgrade head

db-migrate: ## Generate a new Alembic migration (usage: make db-migrate MSG="description")
	cd backend && uv run python -m alembic revision --autogenerate -m "$(MSG)"

db-downgrade: ## Downgrade Alembic by one revision (usage: make db-downgrade or make db-downgrade REV="base")
	cd backend && uv run python -m alembic downgrade $(or $(REV),-1)

db-stop: ## Stop Postgres + Adminer
	docker compose down database adminer

# ──────────────────────────────────────────────
# Docker (everything in containers)
# ──────────────────────────────────────────────

docker-up: ## Start all services in Docker (frontend, backend, DB, adminer)
	docker compose up -d

docker-down: ## Stop all Docker services
	docker compose down

docker-logs: ## Tail logs for all Docker services
	docker compose logs -f

docker-build-up: ## Build and start stack from local Dockerfiles
	docker compose -f docker-compose.yml -f docker-compose.build.yml up --build -d

docker-build-down: ## Stop stack started with docker-build-up
	docker compose -f docker-compose.yml -f docker-compose.build.yml down

# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

cli: ## Run the CLI (usage: make cli ARGS="hello")
	cd backend && uv run python -m cli $(ARGS)

# ──────────────────────────────────────────────
# Code quality
# ──────────────────────────────────────────────

lint: ## Run linting and type-checking (backend + frontend)
	cd backend && uv run bash scripts/lint.sh
	cd frontend && pnpm lint
	cd frontend && pnpm turbo typecheck

format: ## Format backend code with ruff
	cd backend && uv run bash scripts/format.sh

test: ## Run backend tests with coverage
	cd backend && uv run bash scripts/tests-start.sh

# ──────────────────────────────────────────────
# Code generation
# ──────────────────────────────────────────────

generate-client: ## Regenerate frontend API client from backend OpenAPI
	bash scripts/generate-client.sh
