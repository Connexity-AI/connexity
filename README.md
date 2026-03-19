# connexity-evals

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [uv](https://docs.astral.sh/uv/) — `winget install astral-sh.uv`
- [Node.js](https://nodejs.org/) + [pnpm](https://pnpm.io/)
- [GNU Make](https://www.gnu.org/software/make/) — `winget install GnuWin32.Make`

## Quick Start

### Option A — Local dev (DB in Docker, app runs natively)

```bash
# 1. Copy environment variables
cp .env.example .env
cp frontend/apps/web/.env.example frontend/apps/web/.env

# 2. Install dependencies (Python + frontend)
make install

# 3. Start database
make db

# 4. Run migrations and seed data
make db-seed

# 5. Start backend (in one terminal)
make dev

# 6. Start frontend (in another terminal)
make dashboard
```

### Option B — Everything in Docker

```bash
# 1. Copy environment variables
cp .env.example .env
cp frontend/apps/web/.env.example frontend/apps/web/.env

# 2. Start all services (frontend, backend, database, adminer)
make docker-up
```

> Logs: `make docker-logs` — Stop: `make docker-down`

## URLs

| Service  | URL                     |
| -------- | ----------------------- |
| Frontend | http://localhost:3000   |
| Backend  | http://localhost:8000/docs |
| Adminer  | http://localhost:8083   |

## All Commands

Run `make help` to see all available targets.
