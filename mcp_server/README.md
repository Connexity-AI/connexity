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

Local-dev fallbacks are built in:

- `CONNEXITY_API_URL` falls back to `API_URL` and then `http://localhost:8000/api/v1`
- `MCP_PUBLIC_BASE_URL` falls back to `https://${RAILWAY_PUBLIC_DOMAIN}` on Railway

For Railway production, set the same `MCP_CLIENT_SECRET` on both the backend
and MCP services. `MCP_CLIENT_ID` is optional unless you want to override the
built-in `mcp-server` identity. The MCP server uses that shared secret pair
only to call `/internal/token`; the backend returns a short-lived service JWT
that the MCP server then uses for `/mcp/*` requests.
