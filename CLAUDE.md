# Connexity

## What this is

The goal: **an AI assistant (Claude Code or similar) runs operations for an entire fleet
of conversational AI agents, with people approving where it matters.** The assistant
watches, investigates and fixes. People step in when a decision is theirs: approving a
change, settling a business question, owning the client.

Connexity is the framework that makes the assistant able to do that job: the process it
follows, the information it works from (every call, every system the agent touches,
every decision made), the skills and know-how for operating conversational agents, the
verification of its work, and the place where people approve.

Connexity itself never changes an agent: no editing of prompts or workflows, no
deploying, no chat. The assistant does the work; people approve.

The code is mostly Connexity 1.x, being rebuilt in place into 2.0. Do not treat existing
patterns as the direction.

## Read first

| Document | For |
|---|---|
| [`REBUILD.md`](./REBUILD.md) | Status, the next slice, decisions. Every session, first. |
| [`docs-internal/development-lifecycle.md`](./docs-internal/development-lifecycle.md) | How we work. The rules below are its short form. |
| [`docs-internal/`](./docs-internal/) | How each part is designed, e.g. [`checks-and-incidents.md`](./docs-internal/checks-and-incidents.md). Read the docs your slice cites. |
| [`plans/README.md`](./plans/README.md) | One plan per pull request; the plan is what gets reviewed. |
| `backend/CLAUDE.md`, `frontend/CLAUDE.md` | Conventions, loaded when you work there. |
| `README.md`, `CLI_README.md`, `docs/` | Describe 1.x, not where the product is going. |

## The rules, in short

Each is explained in the lifecycle guide; the section is in brackets.

1. One session, one slice from `REBUILD.md`. Do not widen it. (3)
2. Every pull request carries a plan, approved before any code, with its Outcome filled
   in before the pull request opens. (3)
3. Mark statements Decided, Proposed or Open. Only Dmytro's own words make something
   Decided. (4)
4. Do not grade your own work. Run `/code-review` before opening a pull request. (2, 5)
5. Never weaken a test, type check or lint rule without saying so at the top of the pull
   request. (5)
6. You test the backend through its API; Dmytro tests the screens. (5)
7. Delete, do not deprecate. Ask before deleting anything `REBUILD.md` does not list. (6)
8. Build nothing lifecycle section 6 rules out. Add a check only when Dmytro asks for it by
   name. (6)
9. UI changes start in the design, and the design never falls behind the code. (3)
10. Every feature ships with its MCP tools: whatever the platform does, the user's
    assistant can do through MCP. (6)
11. The repo is public: no real call data, client names or secrets. (6)
12. No AI attribution in commits or pull requests. (7)
13. End every reply with "Next step from you:". (10)

## Commands

```bash
make install          # Python (uv) and frontend (pnpm) dependencies
make db               # Postgres + Adminer in Docker
make db-seed          # migrations + superuser
make dev              # FastAPI on :8000
make dashboard        # Next.js on :3000
make mcp              # MCP server
make check            # every gate a pull request must pass; run before every push
make db-reset         # DELETE the local database and rebuild it from migrations
make lint             # backend + frontend lint and types
make test             # backend tests with coverage
make generate-client  # regenerate the frontend API client
make db-migrate MSG="description"   # new Alembic revision
```

## Architecture that survives the rebuild

- **Type chain:** SQLModel, FastAPI, OpenAPI, Hey API codegen, TypeScript SDK. No
  hand-written types in its place. Never edit `frontend/apps/web/src/client/`; it is
  generated (`make generate-client`).
- **Multitenancy:** every tenant-owned row carries `company_id`.
- **Auth:** HttpOnly cookie JWT for the web app; OAuth bearer tokens for MCP.
- **MCP** is a thin adapter (`mcp_server/`) that forwards the user's token to backend
  `/api/v1/mcp/*` routes. It is the assistant's main way into the product.
- **Environment variables** are validated at runtime (Pydantic in the backend, Zod in the
  frontend). The root `.env` is the only env file; add new ones to `.env.example`.
- **Tooling:** `uv` for Python, `pnpm` for the frontend.
