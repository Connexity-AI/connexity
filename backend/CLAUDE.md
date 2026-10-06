# Backend conventions

Applies to all Python in `backend/` and `mcp_server/`.

## Checks

```bash
cd backend
uv run ruff check app cli scripts          # lint
uv run ruff format --check app cli scripts  # format check
uv run pyright                              # type check
uv run pytest app/tests -v                  # tests
```

Tests run against a separate `app_test` database in the same Postgres container.
`backend/conftest.py` creates it and applies migrations on first run; it is safe to wipe.

If the root `.env` sets `DATABASE_URL` (a hosted database), it overrides `POSTGRES_*` and
the test safety check refuses to run. Never point tests or migrations at that database.
Override `DATABASE_URL` in the shell for the test run, pointing at a local or throwaway
Postgres with a database named `app_test`:

```bash
docker run -d --rm --name connexity-test-db -e POSTGRES_PASSWORD=password -p 127.0.0.1:55000:5432 postgres:17-alpine
DATABASE_URL=postgresql://postgres:password@127.0.0.1:55000/app_test uv run pytest app/tests -q
```

After any route or model change, run `bash scripts/generate-client.sh` from the repo root.

## Layering

- **Routes orchestrate, CRUD queries.** All database logic goes in `app/crud/`, not in
  route handlers.
- **`response_model=` is the public contract.** Never return a `table=True` model
  directly.
- **Dependencies** via FastAPI `Depends()` for auth and sessions. Do not create sessions
  by hand in routes.
- **Every tenant-owned row carries `company_id`** and every query filters on it.
- **MCP tools stay thin.** Business logic lives in backend `/api/v1/mcp/*` routes; the
  adapter in `mcp_server/` forwards the user's bearer token. See
  `docs-internal/mcp-architecture.md`.
- **Provider code is read-only.** No call in this codebase deploys to, or mutates, a
  voice platform, n8n or a CRM.

## Style

- **Python 3.12+.** `type` aliases, `X | Y` unions (not `Union` or `Optional`).
- **Type hints on every signature**, including `-> None`.
- **Pydantic or SQLModel models** for anything crossing an API boundary. No raw dicts
  for request or response bodies.
- **No `Any`** unless interfacing with an untyped external library.
- **f-strings** only.
- **Absolute imports** (`from app.models import ...`), stdlib then third-party then
  local. No wildcard imports.
- **Docstrings** only on public functions with non-obvious behaviour, Google style.
- **Errors:** raise `HTTPException` in routes. Catch specific exception types. Never
  swallow an exception silently.
- **Async:** `async def` for handlers that do I/O, plain `def` otherwise.

## External calls

Every call to a provider, n8n, a CRM or a model has tests for timeout, empty response
and malformed response. Use `respx` to mock HTTP.

## Migrations

Alembic revisions live in `app/alembic/versions/`. After a model change:

```bash
cd backend && alembic revision --autogenerate -m "description"
```

Review the generated file, then run `bash scripts/prestart.sh`.

- **Models are the single description of the schema.** Declare every index, partial
  index, constraint and `ondelete` rule on the model, never in a migration only. The
  test `test_models_match_migrated_schema` fails on any drift; `uv run alembic check`
  shows it.
- **Enum columns** use `sa_type=enum_type(MyEnum)` from `app.models.columns`: a VARCHAR
  holding the member's value, no Postgres ENUM type.
- The history starts at `0001_baseline`. See `docs-internal/migrations.md`.
