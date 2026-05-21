# Connexity MCP Server

Standalone MCP adapter service for Connexity.

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
- `MCP_CLIENT_ID` optional, defaults to `mcp-server`
- `MCP_CLIENT_SECRET`
- `MCP_HOST`
- `MCP_PORT`
- `MCP_PATH`
- `MCP_SERVER_NAME`
- `MCP_PUBLIC_BASE_URL`
- `MCP_OAUTH_ISSUER_URL`
- `MCP_OAUTH_AUDIENCE` optional, defaults to the public MCP URL
- `MCP_OAUTH_REQUIRED_SCOPES` optional, comma- or space-separated
- `MCP_OAUTH_DISCOVERY_URL` optional override
- `MCP_OAUTH_JWKS_URL` optional override
- `MCP_OAUTH_RESOURCE_SERVER_URL` optional override; defaults to `${MCP_PUBLIC_BASE_URL}${MCP_PATH}`

Local-dev fallbacks are built in:

- `CONNEXITY_API_URL` falls back to `API_URL` and then `http://localhost:8000/api/v1`
- `MCP_PUBLIC_BASE_URL` falls back to `https://${RAILWAY_PUBLIC_DOMAIN}` on Railway

For Railway production, set the same `MCP_CLIENT_SECRET` on both the backend
and MCP services. `MCP_CLIENT_ID` is optional unless you want to override the
built-in `mcp-server` identity. The MCP server uses that shared secret pair
only to call `/internal/token`; the backend returns a short-lived service JWT
that the MCP server then uses for `/mcp/*` requests. If `MCP_CLIENT_SECRET`
is missing on the MCP side, the server now fails at startup instead of waiting
until the first Claude tool call.

## Mandatory OAuth for MCP transport

OAuth is mandatory for this MCP server. If OAuth resource-server configuration
is missing, the server should fail at startup rather than expose tools
anonymously.

Configure the MCP service as an OAuth-protected resource server:

- set `MCP_PUBLIC_BASE_URL` to the HTTPS origin Claude will reach
- set `MCP_OAUTH_ISSUER_URL` to the Connexity backend public origin
- optionally set `MCP_OAUTH_AUDIENCE`; if omitted it defaults to `${MCP_PUBLIC_BASE_URL}${MCP_PATH}`
- optionally set `MCP_OAUTH_REQUIRED_SCOPES`, for example `mcp:access`

The Connexity backend includes the OAuth authorization server and Dynamic Client
Registration endpoints Claude needs, so users should only need to paste the MCP
URL into Claude. The backend issuer exposes metadata, JWKS, `/oauth/register`,
`/oauth/authorize`, and `/oauth/token`.
