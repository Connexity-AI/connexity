# connexity-evals Makefile
# Two modes: local (no Docker for app, just DB) and docker (everything in Docker)

.PHONY: help install dev dashboard db db-seed db-stop \
        docker-up docker-down docker-logs \
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
	cd backend && uv venv && uv sync
	cd frontend && pnpm install

dev: ## Start FastAPI backend (local, requires DB running)
	cd backend && uv run uvicorn app.main:app --reload

dashboard: ## Start Next.js dev server
	cd frontend && pnpm dev

db: ## Start Postgres + Adminer in Docker
	docker compose up -d database adminer

db-seed: ## Run migrations and seed data
	cd backend && uv run bash scripts/prestart.sh

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

# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

cli: ## Run the CLI (usage: make cli ARGS="hello")
	cd backend && uv run python -m cli $(ARGS)

# ──────────────────────────────────────────────
# Code quality
# ──────────────────────────────────────────────

lint: ## Run ruff + mypy on backend
	cd backend && uv run bash scripts/lint.sh

format: ## Format backend code with ruff
	cd backend && uv run bash scripts/format.sh

test: ## Run backend tests with coverage
	cd backend && uv run bash scripts/tests-start.sh

# ──────────────────────────────────────────────
# Code generation
# ──────────────────────────────────────────────

generate-client: ## Regenerate frontend API client from backend OpenAPI
	bash scripts/generate-client.sh
