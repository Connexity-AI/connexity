# Connexity

## What this is

Connexity is the system of record and independent verifier for voice AI agents. An AI
assistant (Claude Code or another) does the engineering on a voice agent. Connexity
holds the spec, the call traces, the versions and the test verdicts, checks every real
call, detects incidents, and tells the human what needs a decision. The human decides
and approves.

Connexity never writes fixes, never deploys, and never talks back. It has no chat.

## Current state: mid-rebuild

The code in this repo is mostly **Connexity 1.x**, an eval and observability platform
with a builder UI (prompt editors, test creation forms, deploy buttons). That product is
being rebuilt in place into 2.0. Much of what you see in the code is scheduled for
deletion, so do not treat existing patterns as the direction.

**Before doing anything, read [`REBUILD.md`](./REBUILD.md).** It has the current status,
the next slice, what is kept, frozen and deleted, and the open questions.

| Document | Read it for |
|---|---|
| [`REBUILD.md`](./REBUILD.md) | Status, next slice, carry-over map, decisions. Read every session. |
| [`Connexity 2.0.md`](./Connexity%202.0.md) | The vision. Read the sections your slice cites. |
| [`docs-internal/development-lifecycle.md`](./docs-internal/development-lifecycle.md) | How we work: the slice loop, verification, decisions. |
| `backend/CLAUDE.md`, `frontend/CLAUDE.md` | Language and framework conventions. |
| `README.md`, `CLI_README.md`, `docs/` | Describe 1.x. Not a guide to where the product is going. |

## Rules for every session

1. **One session, one slice** from `REBUILD.md`. Do not widen it. Note anything else you
   find in `REBUILD.md` instead of fixing it.
2. **End by updating `REBUILD.md`:** the status table, the session log, and the decision
   log if something was decided.
3. **Do not record a decision Dmytro did not make.** Mark statements Decided, Proposed
   or Open. Only his explicit words make something Decided.
4. **Do not grade your own work.** State the done-when before building, report check
   results with their output, and run `/code-review` in a fresh context before asking
   for review.
5. **Never weaken a test, type check or lint rule to make a change pass** without saying
   so at the top of the PR description.
6. **Delete, do not deprecate.** No compatibility is owed to 1.x. Remove dead code with
   its tests, routes, generated client and docs in the same PR. Before deleting anything
   not listed in `REBUILD.md`, ask.
7. **Do not build what the vision rules out:** chat, editors for prompts or workflows,
   creation forms, deploying or writing to providers, features about a system rather
   than an agent's conversation.
8. **The repo is public.** Never commit real call data, client names or secrets.

## Commands

```bash
make install          # Python (uv) and frontend (pnpm) dependencies
make db               # Postgres + Adminer in Docker
make db-seed          # migrations + superuser
make dev              # FastAPI on :8000
make dashboard        # Next.js on :3000
make mcp              # MCP server
make check            # every gate a PR must pass, with per-step timings
make db-reset         # DELETE the local database and rebuild it from migrations
make lint             # backend + frontend lint and types
make test             # backend tests with coverage
make generate-client  # regenerate the frontend API client
make db-migrate MSG="description"   # new Alembic revision
```

### What to run before committing

Run `make check` before every push. It runs the same gates as CI (backend lint, format,
types, tests with the coverage floor, MCP tests, frontend lint and types, generated
client freshness) and takes about a minute and a half.

While iterating, run only what your change touches; the commands are in
`backend/CLAUDE.md` and `frontend/CLAUDE.md`. After a backend route or model change,
run `bash scripts/generate-client.sh`.

### Hooks

`.claude/settings.json` is tracked and applies to every session:

- Edits under `frontend/apps/web/src/client/` are blocked. Regenerate instead.
- After an edit under `backend/app/models/` or `backend/app/api/routes/`, the session is
  reminded to add a migration and regenerate the client.

Personal settings go in `.claude/settings.local.json`, which is ignored.

## Architecture that survives the rebuild

- **Type chain:** SQLModel → FastAPI → OpenAPI → Hey API codegen → TypeScript SDK. Do
  not break it with hand-written types.
- **Never edit `frontend/apps/web/src/client/`.** It is generated.
- **Multitenancy:** every tenant-owned row carries `company_id`.
- **Auth:** HttpOnly cookie JWT for the web app; OAuth bearer tokens for MCP.
- **MCP is a separate thin adapter** (`mcp_server/`) that forwards the user's token to
  backend `/api/v1/mcp/*` routes. It is the assistant's main interface to the product.
- **Environment variables** are validated at runtime (Pydantic `BaseSettings` in the
  backend, Zod in the frontend). Add new ones to the root `.env.example` and the
  schema. The root `.env` is the only env file.
- **Tooling:** `uv` for Python, `pnpm` for the frontend.

## Git

- Base branch is `main`. One slice per branch.
- **Never add AI attribution** to commits, PRs or messages: no `Co-authored-by`, no
  "generated with" lines.
- Use the `/commit` and `/create-pr` skills.
