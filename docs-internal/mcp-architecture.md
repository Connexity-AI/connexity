# MCP Architecture

This document explains how MCP is wired into Connexity and how contributors
should add new MCP tools.

## Why MCP is a separate service

Connexity does not expose MCP directly from the main backend process. Instead it
uses a dedicated adapter in [`mcp_server/`](../mcp_server):

- the backend remains the system of record for agents, drafts, auth, and business rules
- the MCP server handles MCP transport, MCP-specific OAuth requirements, and tool registration
- the tool layer stays thin by forwarding authenticated requests into backend `/api/v1/mcp/*` routes

That split keeps MCP transport concerns out of the main application while
reusing the same backend models, auth, and audit trail.

## High-level flow

```text
MCP client (Claude/Desktop/etc.)
  -> MCP HTTP transport on /mcp
  -> FastMCP tool in mcp_server/src/connexity_mcp_server/app.py
  -> tool handler in mcp_server/src/connexity_mcp_server/tools.py
  -> backend client in mcp_server/src/connexity_mcp_server/client.py
  -> backend /api/v1/mcp/* route
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

## Main components

### 1. MCP adapter app

[`mcp_server/src/connexity_mcp_server/app.py`](../mcp_server/src/connexity_mcp_server/app.py)
builds the FastAPI app and the `FastMCP` server.

It is responsible for:

- failing fast when mandatory MCP OAuth config is missing
- creating the backend client and OIDC token verifier
- registering MCP tools with `@mcp_server.tool()`
- mounting the streamable HTTP MCP transport at `MCP_PATH`
- exposing `/healthz`
- proxying OAuth metadata and OAuth endpoints back to the backend
- exposing OAuth protected-resource metadata for MCP clients

This file should stay mostly orchestration-only. Avoid putting business logic
directly here.

### 2. MCP token verification

[`mcp_server/src/connexity_mcp_server/auth.py`](../mcp_server/src/connexity_mcp_server/auth.py)
implements `OidcTokenVerifier`.

It validates:

- issuer
- audience
- JWKS-backed signature
- scopes from `scope` / `scp`

The verifier returns an MCP `AccessToken`, which makes the current bearer token
available to downstream tool code through the MCP auth context.

### 3. Backend forwarding client

[`mcp_server/src/connexity_mcp_server/client.py`](../mcp_server/src/connexity_mcp_server/client.py)
is the adapter's only backend transport layer.

Key rule: it forwards the currently authenticated MCP user's bearer token to the
backend on every `/mcp/*` request.

That is what lets the backend:

- authenticate the request again
- resolve the actual Connexity user
- stamp audit fields such as `created_by`
- keep permission checks in one place

### 4. MCP tool handlers

[`mcp_server/src/connexity_mcp_server/tools.py`](../mcp_server/src/connexity_mcp_server/tools.py)
contains thin async functions that:

- call backend endpoints through `ConnexityBackendClient`
- normalize backend payloads
- return tool-specific Pydantic result models

This is the right place for lightweight shaping such as search filtering or
small response transformations. Do not move core database or ownership logic
here.

### 5. MCP result models

[`mcp_server/src/connexity_mcp_server/models.py`](../mcp_server/src/connexity_mcp_server/models.py)
defines the typed payloads returned to MCP clients.

These models are the MCP-facing contract. Keep them explicit and stable.

### 6. Backend MCP routes

[`backend/app/api/routes/mcp.py`](../backend/app/api/routes/mcp.py) is the
backend entrypoint for MCP-originated actions.

It is protected by
[`require_mcp_user`](../backend/app/api/deps.py), which validates:

- OAuth bearer token presence
- configured MCP audience
- issuer
- `mcp:access` scope
- that `sub` resolves to an active Connexity user

The backend route should own authorization, validation, CRUD calls, and any
state changes.

## Request lifecycle for a tool call

Using `update_agent_prompt` as the example:

1. An MCP client calls the tool on the MCP server.
2. FastMCP authenticates the bearer token using `OidcTokenVerifier`.
3. The registered tool in `app.py` calls `tools.update_agent_prompt(...)`.
4. `tools.py` calls `ConnexityBackendClient.update_agent_draft(...)`.
5. `client.py` reads the current MCP access token from auth context and sends it
   as `Authorization: Bearer ...` to `PUT /api/v1/mcp/agents/{agent_id}/draft`.
6. The backend route validates the token again via `require_mcp_user`.
7. Backend CRUD updates the draft and stamps `created_by` from the MCP user.
8. The backend response is normalized into `UpdateAgentPromptResult` and
   returned to the MCP client.

## Design rules for new tools

When adding a tool, keep the layering consistent:

- put durable business logic in the backend, not the MCP adapter
- keep MCP tool handlers thin and focused on transport-friendly shaping
- return typed result models from `mcp_server/models.py`
- forward the current bearer token instead of inventing service credentials
- add tests on both sides of the boundary

If a tool would require broad search, joins, permissions, or mutation rules,
that logic belongs in backend services/CRUD plus a backend `/mcp` route.

## How to add a new tool

This is the standard workflow.

### 1. Add or extend a backend `/mcp` route

Update [`backend/app/api/routes/mcp.py`](../backend/app/api/routes/mcp.py).

- Reuse `require_mcp_user` through the router dependency.
- Accept narrow request shapes.
- Call backend CRUD/services.
- Return an existing public model or add a new backend response model if needed.

Example shape:

```python
@router.get("/agents/{agent_id}/something")
def get_agent_something(
    session: SessionDep,
    agent_id: uuid.UUID,
) -> SomeResponseModel:
    ...
```

If the endpoint mutates data, use `current_user: McpCurrentUser` and pass
`current_user.id` into the write path for auditability.

### 2. Add a backend client method in the MCP adapter

Update
[`mcp_server/src/connexity_mcp_server/client.py`](../mcp_server/src/connexity_mcp_server/client.py).

Add a method that maps directly to the backend route:

```python
async def get_agent_something(self, agent_id: str) -> dict[str, Any]:
    return await self._request_json("GET", f"/mcp/agents/{agent_id}/something")
```

Keep the client generic. It should only handle HTTP transport, JSON parsing, and
error conversion.

### 3. Add an MCP-facing result model

Update
[`mcp_server/src/connexity_mcp_server/models.py`](../mcp_server/src/connexity_mcp_server/models.py).

Define the typed return value the MCP client should see:

```python
class AgentSomethingResult(BaseModel):
    agent_id: str
    value: str | None = None
```

### 4. Add the tool handler

Update
[`mcp_server/src/connexity_mcp_server/tools.py`](../mcp_server/src/connexity_mcp_server/tools.py).

This function should call the backend client and normalize the payload:

```python
async def get_agent_something(
    client: ConnexityBackendClient,
    agent_id: str,
) -> AgentSomethingResult:
    payload = await client.get_agent_something(agent_id)
    return AgentSomethingResult(
        agent_id=agent_id,
        value=_string_or_none(payload.get("value")),
    )
```

### 5. Register the tool with FastMCP

Update
[`mcp_server/src/connexity_mcp_server/app.py`](../mcp_server/src/connexity_mcp_server/app.py).

- import the result model
- import the handler from `tools.py`
- register a new `@mcp_server.tool()` function

Example:

```python
@mcp_server.tool()
async def get_agent_something(agent_id: str) -> AgentSomethingResult:
    return await _get_agent_something(client=backend_client, agent_id=agent_id)
```

The registered function should stay minimal. Put transformation logic in
`tools.py`.

### 6. Add tests

At minimum, cover both layers.

Backend route tests:

- file: [`backend/app/tests/api/routes/test_mcp.py`](../backend/app/tests/api/routes/test_mcp.py)
- verify auth requirements
- verify the route returns the expected payload
- verify audit fields on mutations

MCP adapter tests:

- file: [`mcp_server/tests/test_client.py`](../mcp_server/tests/test_client.py)
- verify the adapter forwards the current bearer token to backend `/mcp/*`

Add transport/auth tests in
[`mcp_server/tests/test_auth.py`](../mcp_server/tests/test_auth.py) only when
the new tool changes MCP auth behavior, metadata exposure, or startup config.

### 7. Run the local checks

Typical commands:

```bash
cd mcp_server
uv run pytest

cd ../backend
uv run pytest app/tests/api/routes/test_mcp.py
```

For a full manual run from repo root:

```bash
make dev
make mcp
```

## Current implementation map

Current MCP tools map to backend routes like this:

| MCP tool | Adapter handler | Backend route |
|---|---|---|
| `list_agents` | `tools.list_agents` | `GET /api/v1/mcp/agents` |
| `find_agents` | `tools.find_agents` | `GET /api/v1/mcp/agents` then local filtering in adapter |
| `get_agent_draft` | `tools.get_agent_draft` | `GET /api/v1/mcp/agents/{agent_id}/draft` |
| `update_agent_prompt` | `tools.update_agent_prompt` | `PUT /api/v1/mcp/agents/{agent_id}/draft` |

`find_agents` is the one notable exception where the adapter performs a small
read-only aggregation over paginated backend results. That is acceptable because
it does not change authorization or state.

## What not to do

Avoid these patterns:

- putting database logic directly in `mcp_server/tools.py`
- bypassing backend `/mcp` routes and calling internal backend services from the MCP process
- introducing service-to-service secrets for normal user-scoped tool calls
- returning raw backend payloads when an explicit MCP result model would be clearer
- skipping backend tests because the MCP layer already has tests
