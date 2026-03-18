# Local setup dev

## Database

```bash
# From project root
cd ~/Desktop/full-stack-fastapi-template-nextjs

# Run just Postgres database service
docker compose up -d db

# Needs activated venv and Python dependencies

# From /backend
cd backend/

# Await db, run migrations and seed
bash scripts/prestart.sh

# Run just database migrations
alembic upgrade head

# If changed models generate migration
alembic revision --autogenerate -m "e.g. Add column last_name to User model"
```

## Backend

```bash
# From /backend
cd ./backend

# Create virtual environment
uv venv

# Activate the environment
source .venv/bin/activate

# Install dependencies
uv sync

# Start the FastAPI development server
uvicorn app.main:app --reload
```

## Lint and format

```bash
# From /backend
cd backend/

# Lint and format
bash scripts/lint.sh
bash scripts/format.sh

# Run pre-commit manually
uv run pre-commit run --all-files
```

## Frontend

```bash
# From project root
cd ~/Desktop/full-stack-fastapi-template-nextjs

# Generate client
bash scripts/generate-client.sh

# Run dev
cd frontend
pnpm dev
```

## Development URLs

```bash
# Frontend (todo)
http://localhost:5173

# Backend (root 404 route)
http://localhost:8000

# Automatic Interactive Docs (Swagger UI)
http://localhost:8000/docs

# Automatic Alternative Docs (ReDoc)
http://localhost:8000/redoc

# openapi.json
http://localhost:8000/api/v1/openapi.json
```

## Other containers

#### (his Docker setup)

```bash
# Adminer
http://localhost:8080

# Traefik UI
http://localhost:8090

# MailCatcher
http://localhost:1080
```

## Docker setup dev

```bash
# Create a virtual environment
uv venv

# Activate the environment
source .venv/bin/activate

# Build the containers
docker compose build

# Start the database container
docker compose up -d db

# Run Alembic migrations
docker compose run backend --rm alembic head

# Start all services
docker compose up

# In Docker backend available on 8080, not 8000
http://localhost:8080/docs
```
