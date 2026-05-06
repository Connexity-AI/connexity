# connexity

Open-source eval platform for voice and text agents. You bring an agent (your own HTTP endpoint or one authored on the platform), define test cases and scenarios, and get pass/fail verdicts, regression checks against a baseline, and AI-powered suggestions for fixing failures.

What's in the box:

- **Eval runs** — orchestrated multi-turn conversations against your agent, scored by an LLM judge across 8 default metrics plus any custom metrics you define
- **Pass/fail thresholds** — every run is gated on `metrics_pass_threshold` (weighted score) and `cases_pass_threshold` (fraction of cases passing); see [docs/scoring-and-thresholds.md](docs/scoring-and-thresholds.md)
- **Agent versioning** — draft / publish lifecycle, immutable history, version-pinned runs, side-by-side prompt diffs
- **Run-to-run comparison** — regression verdict with overridable thresholds, plus optional AI cause-analysis
- **Prompt editor** — chat-driven prompt iteration with live diffs, AI suggestions, and per-agent guidelines
- **Platform-side agent simulator** — build a Connexity-hosted agent (system prompt + tools) without standing up your own HTTP service
- **Retell integration** — sync recorded calls, deploy agent versions to Retell with an optional eval-gate that blocks deploys when thresholds fail
- **`connexity-cli`** — a thin Python CLI covering the public REST surface; ideal for CI gates ([CLI_README.md](CLI_README.md))

## Quick start (Docker)

Prebuilt images live on [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry). Use a **public** package (or inherit visibility from a public repo) so pulls work without logging in.

```bash
git clone https://github.com/Connexity-AI/connexity.git
cd connexity

cp .env.example .env
# Edit .env: set SITE_URL, JWT_SECRET_KEY, ENCRYPTION_KEY, POSTGRES_PASSWORD, optional API keys.

docker compose up
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **API docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **DB UI (pgweb)**: [http://localhost:8083](http://localhost:8083)

The compose file sets **`API_URL=http://backend:8000`** inside the frontend container so the Next.js server talks to FastAPI over the Docker network. You usually only set **`SITE_URL`** to the URL people open in the browser (`http://localhost:3000` locally, or `https://…` when hosted).

**Forks / custom images**: override in `.env`:

```env
CONNEXITY_BACKEND_IMAGE=ghcr.io/your-org/connexity-backend:latest
CONNEXITY_FRONTEND_IMAGE=ghcr.io/your-org/connexity-frontend:latest
```

**Build images locally** (contributors):

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build
# or: make docker-build-up
```

## Local development (DB in Docker, apps on host)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/), [uv](https://docs.astral.sh/uv/), [Node.js](https://nodejs.org/) + [pnpm](https://pnpm.io/), [GNU Make](https://www.gnu.org/software/make/).

One env file at the repo root (same `.env` as Docker). It includes **`API_URL=http://localhost:8000`** and **`POSTGRES_SERVER=localhost`** so the backend and Next.js dev server reach Postgres on the host port.

```bash
cp .env.example .env
make install
make db
make db-upgrade
make dev          # terminal 1 — backend
make dashboard    # terminal 2 — frontend (loads root .env)
```

## CLI against a hosted instance

Point the CLI at the **public API base URL** (same host as the app if you reverse-proxy `/api/v1`, or a dedicated API host). See [`.env.example`](.env.example) (`CONNEXITY_CLI_API_URL` / `CONNEXITY_CLI_API_TOKEN`).

## Accounts

The database starts empty. Sign up in the UI or via `POST /api/v1/users/signup`.

## Further docs

- [docs/running.md](docs/running.md) — detailed local setup
- [docs/scoring-and-thresholds.md](docs/scoring-and-thresholds.md) — judge scoring formula and run-level pass/fail thresholds
- [docs/judge-criteria.md](docs/judge-criteria.md) — default and custom metric definitions
- [docs/data-model.md](docs/data-model.md) — agent / eval-config / run / test-case relationships
- [docs/agent-contract.md](docs/agent-contract.md) — HTTP contract for bring-your-own-agent
- [docs/test-case-schema.md](docs/test-case-schema.md) — scenario v2 schema with personas
- [docs/migrations.md](docs/migrations.md) — Alembic workflow
- [CLI_README.md](CLI_README.md) — `connexity-cli` reference
- `make help` — Make targets
