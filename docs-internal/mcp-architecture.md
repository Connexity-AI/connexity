# MCP Architecture

How MCP is wired into Connexity, the rules every tool follows, and how to add one.

MCP is the assistant's main way into the product. Every feature ships its tools
(`CLAUDE.md` rule 10): few, shaped around the work, scoped to a workspace, paginated, and
answering in the standard shape below.

## Why MCP is a separate service

Connexity does not expose MCP from the main backend process. A dedicated adapter in
[`mcp_server/`](../mcp_server) handles MCP transport, MCP-specific OAuth and tool
registration, and forwards each call to backend `/api/v1/mcp/*` routes with the user's
own token. The backend stays the system of record: it authenticates again, decides
access, writes the answer and records who did what.

## High-level flow

```text
MCP client (Claude Code, ChatGPT, …)
  -> MCP HTTP transport on /mcp
  -> FastMCP tool in mcp_server/src/connexity_mcp_server/app.py
  -> tool handler in mcp_server/src/connexity_mcp_server/tools.py
  -> backend client in mcp_server/src/connexity_mcp_server/client.py
  -> backend /api/v1/mcp/workspaces/{workspace_id}/… route
  -> CRUD/services/models in backend
```

OAuth discovery and token issuance follow a parallel path:

```text
MCP client
  -> MCP server /.well-known/* and /oauth/*
  -> proxy to backend OAuth endpoints
  -> backend issues OAuth tokens
  -> MCP server validates bearer token and forwards it to backend /mcp routes
```

## The rules every tool follows

### Connections are per user

An OAuth token belongs to the person who approved the connection (its `sub`), and
refresh tokens are stored per person and client. A person may connect as many
assistants as they like. Each reaches exactly the workspaces that person can reach
(Decided 2026-11-12). The token carries no workspace.

### Every call is scoped to a workspace

A workspace is a company: one client of an agency. Every backend `/mcp` route except
`GET` and `POST /mcp/workspaces` has the workspace in its path,
`/api/v1/mcp/workspaces/{workspace_id}/…`, and depends on `McpWorkspaceDep`
(`require_mcp_workspace` in `backend/app/api/deps.py`).

- Access is decided in one place: `backend/app/crud/workspace.py`. A person reaches
  the workspaces they are a member of (`workspace_member`). The workspace open on the
  web (`user.company_id`) plays no part in MCP: every call names its workspace.
- A workspace the person cannot reach answers 404 "Workspace not found", the same as one
  that does not exist.
- `test_every_mcp_route_is_scoped_to_a_workspace` fails on any `/mcp` route without the
  workspace in its path.
- Tools take `workspace_id` as a required argument. `list_workspaces` is where the
  assistant gets it.

### One answer shape

Every route answers with `McpAnswer` (`backend/app/models/mcp.py`), and every tool
returns it unchanged (`Answer` in `mcp_server/.../models.py`):

| Field | What it holds |
|---|---|
| `data` | The facts: the result of the call |
| `rules` | The rules that apply to what was returned, one sentence each. Short; not documentation |
| `next_steps` | Steps the assistant can take next, in order, naming the tool to call |
| `guide` | URI of the guide for this part of Connexity (`connexity://guides/<name>`) |
| `next_cursor` | On lists: pass back as `cursor` for the next page; empty on the last page |

The backend writes `rules` and `next_steps`, because it knows the state; the adapter
only validates and passes them through.

Errors use the same idea. A route raises `HTTPException` with an `McpErrorDetail` as its
`detail`: `error`, `next_steps` and `guide`. The adapter turns it into one line the
assistant can act on: "Workspace not found. Next steps: 1. Call `list_workspaces` …
Guide: connexity://guides/workspaces". FastAPI's 422 for an invalid argument becomes
the same kind of line, naming the argument.

### Pagination

Lists take `cursor` and `limit` (default 25, at most 100) and return `next_cursor`. The
cursor is opaque to the assistant. A cursor that does not decode answers 400 with a next
step to start over.

### Instructions and guides

- The MCP server sends short **connect instructions** (`INSTRUCTIONS` in
  `mcp_server/.../guides.py`): what Connexity is, start with `list_workspaces`, follow
  `rules`, read the `guide`.
- **Guides** are markdown files in `mcp_server/src/connexity_mcp_server/guides/`, listed
  in `GUIDES` and served as MCP resources at `connexity://guides/<name>`. A feature that
  adds tools adds or extends its guide and points its answers' `guide` at it.

## Main components

### MCP adapter app (`mcp_server/.../app.py`)

Builds the FastAPI app and the `FastMCP` server. It fails fast when MCP OAuth config is
missing, registers tools and guide resources, mounts the streamable HTTP transport at
`MCP_PATH`, exposes `/healthz`, proxies OAuth metadata and endpoints to the backend, and
serves the OAuth protected-resource metadata. Keep it orchestration only.

### MCP token verification (`mcp_server/.../auth.py`)

`OidcTokenVerifier` validates issuer, audience, JWKS signature and scopes, and puts the
token in the MCP auth context for the client to forward.

### Backend forwarding client (`mcp_server/.../client.py`)

The adapter's only backend transport. It forwards the current user's bearer token on
every request and turns error answers into text the assistant can act on.

### Tool handlers and result models (`tools.py`, `models.py`)

Thin functions that call the client and validate the payload into a typed `Answer`. No
database, ownership or business logic here.

### Backend MCP routes (`backend/app/api/routes/mcp.py`)

Protected by `require_mcp_user` (bearer token, audience, issuer, `mcp:access` scope, an
active user) and, below `/mcp/workspaces/{workspace_id}`, by `require_mcp_workspace`.
They own validation, CRUD calls, state changes and the answer's rules and next steps.

## How to add a tool

1. **Prefer extending a tool.** A new filter or field on an existing tool beats a
   near-duplicate tool.
2. **Backend route** in `backend/app/api/routes/mcp.py`, under
   `/workspaces/{workspace_id}/…`, with `workspace: McpWorkspaceDep`. Query through
   `app/crud/` with `workspace.id` as the company. Answer `McpAnswer[YourModel]` with
   rules, next steps and a guide. Raise errors with an `McpErrorDetail`. On writes, take
   `current_user: McpCurrentUser` and record who did it.
3. **Client method** in `client.py`, mapping one-to-one to the route.
4. **Result model** in `models.py`: `Answer[YourModel]`.
5. **Handler** in `tools.py`: call the client, `model_validate` the payload.
6. **Register** it in `app.py` with a docstring the assistant reads: what it returns and
   which arguments matter.
7. **Guide:** add or extend the guide its answers point to, and list it in `GUIDES`.
8. **Tests on both sides:** backend route tests in
   `backend/app/tests/api/routes/test_mcp.py` (answer shape, an unreachable workspace,
   paging, audit fields on writes); adapter tests in `mcp_server/tests/` (token
   forwarded, arguments sent, answer kept).
9. **Run** `make check`.

## Current tools

| MCP tool | Backend route |
|---|---|
| `list_workspaces` | `GET /api/v1/mcp/workspaces` |
| `create_workspace(name)` | `POST /api/v1/mcp/workspaces` |
| `get_readiness(workspace_id)` | `GET /api/v1/mcp/workspaces/{workspace_id}/readiness` |
| `list_agents(workspace_id, query?, cursor?, limit?)` | `GET /api/v1/mcp/workspaces/{workspace_id}/agents` |

## What not to do

- Database or ownership logic in `mcp_server/`.
- Calling backend internals from the MCP process instead of `/mcp` routes.
- Service-to-service secrets for user-scoped calls.
- A route without the workspace in its path, or deciding access anywhere but
  `crud/workspace.py`.
- Raw backend payloads instead of the answer shape.
- Skipping backend tests because the adapter has tests.
