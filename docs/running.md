# Local dev setup

Install and run project locally for development.

## Environment variables

Clone the repository, create `.env` files for backend and frontend and populate them. Available environment variables: 

- Backend: [.env.example](../.env.example).
- Frontend: [frontend/apps/web/.env.example](../frontend/apps/web/.env.example).

```bash
# Clone repository
git clone git@github.com:space-step/connexity-evals.git

# Create backend .env file
cp .env.example .env

# Create frontend .env file
cd frontend/apps/web
cp .env.example .env
```

## Backend

Create and activate virtual environment, install dependencies and run FastAPI dev server.

```bash
# From /backend
cd ./backend

# Create virtual environment
uv venv

# Activate the environment
source .venv/bin/activate

# Install dependencies
uv sync

# Start the FastAPI development server (after database)
uvicorn app.main:app --reload

# Automatic Interactive Docs (Swagger UI)
http://localhost:8000/docs

# Run backend tests (cd ./backend)
bash ./scripts/test.sh
```

## Database

Run Postgres container and run migrations.

```bash
# From project root
cd ~/Desktop/connexity-evals

# Run just Postgres database service
docker compose up -d database adminer

# From /backend
cd ./backend

# Needs activated venv and Python dependencies

# Await db and run migrations (must have .env), reminder: MUST rerun after delete db in dev
bash scripts/prestart.sh

# Apply just database migrations
alembic upgrade head

# If changed models generate migration
alembic revision --autogenerate -m "e.g. Add column last_name to User model"
```

## Frontend

Generate OpenAPI client and run Next.js dev server.

```bash
# From project root, with activated backend/ venv, fix this
cd ~/Desktop/connexity-evals

# Generate client (needs activated venv)
bash scripts/generate-client.sh

# From /frontend
cd ./frontend

# Run dev
pnpm dev
```
