# Connexity MCP Server

Standalone MCP adapter service for Connexity.

This package is the thin transport layer between an MCP client such as Claude
and the Connexity backend. It owns:

- MCP transport and tool registration
- MCP OAuth resource-server validation
- OAuth metadata proxying back to the main backend
- forwarding authenticated tool requests to backend `/api/v1/mcp/*` routes

For the contributor-facing architecture and tool-extension guide, see
[`../docs-internal/mcp-architecture.md`](../docs-internal/mcp-architecture.md).

## Current tools

The adapter currently exposes four MCP tools:

- `list_agents`
- `find_agents`
- `get_agent_draft`
- `update_agent_prompt`

## Run locally

From the repo root:

```bash
make mcp
```

That target loads the repo root `.env`, syncs `mcp_server` dependencies, and starts
the MCP server.

## Configuration

The server reads these environment variables:

- `CONNEXITY_API_URL`
- `MCP_HOST`
- `MCP_PORT`
- `MCP_PATH`
- `MCP_SERVER_NAME`
- `MCP_PUBLIC_BASE_URL`
- `MCP_OAUTH_ISSUER_URL`
- `MCP_OAUTH_AUDIENCE` optional, defaults to the public MCP URL
- `MCP_OAUTH_REQUIRED_SCOPES` optional, comma- or space-separated; defaults to `mcp:access`
- `MCP_OAUTH_DISCOVERY_URL` optional override
- `MCP_OAUTH_JWKS_URL` optional override
- `MCP_OAUTH_RESOURCE_SERVER_URL` optional override; defaults to `${MCP_PUBLIC_BASE_URL}${MCP_PATH}`

Local-dev fallbacks are built in:

- `CONNEXITY_API_URL` falls back to `API_URL` and then `http://localhost:8000/api/v1`
- `MCP_PUBLIC_BASE_URL` falls back to `https://${RAILWAY_PUBLIC_DOMAIN}` on Railway

The MCP server forwards the authenticated user's MCP OAuth access token to the
Connexity backend for `/mcp/*` requests. The backend validates that token and
uses the user id for audit fields, while MCP actions remain platform-scoped.

## Mandatory OAuth for MCP transport

OAuth is mandatory for this MCP server. If OAuth resource-server configuration
is missing, the server should fail at startup rather than expose tools
anonymously.

Configure the MCP service as an OAuth-protected resource server:

- set `MCP_PUBLIC_BASE_URL` to the HTTPS origin Claude will reach
- set `MCP_OAUTH_ISSUER_URL` to the Connexity backend public origin
- optionally set `MCP_OAUTH_AUDIENCE`; if omitted it defaults to `${MCP_PUBLIC_BASE_URL}${MCP_PATH}`
- optionally set `MCP_OAUTH_REQUIRED_SCOPES`; it defaults to `mcp:access`

The Connexity backend includes the OAuth authorization server and Dynamic Client
Registration endpoints Claude needs, so users should only need to paste the MCP
URL into Claude. The backend issuer exposes metadata, JWKS, `/oauth/register`,
`/oauth/authorize`, and `/oauth/token`.
