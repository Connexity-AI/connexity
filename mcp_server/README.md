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
- `CONNEXITY_API_TOKEN`
- `CONNEXITY_EMAIL`
- `CONNEXITY_PASSWORD`
- `CONNEXITY_USE_SAVED_CLI_CREDENTIALS`
- `MCP_HOST`
- `MCP_PORT`
- `MCP_PATH`
- `MCP_SERVER_NAME`

Local-dev fallbacks are built in:

- `CONNEXITY_API_URL` falls back to `API_URL` and then `http://localhost:8000/api/v1`
- auth falls back from `CONNEXITY_API_TOKEN` to saved CLI credentials, then
  `CONNEXITY_EMAIL` / `CONNEXITY_PASSWORD`, then `FIRST_SUPERUSER` /
  `FIRST_SUPERUSER_PASSWORD`
- `MCP_PUBLIC_BASE_URL` falls back to `https://${RAILWAY_PUBLIC_DOMAIN}` on Railway
- `CONNEXITY_USE_SAVED_CLI_CREDENTIALS` defaults to `false` on Railway and `true`
  in local development
