# Railway template blueprint

This repository can express most of the Railway deployment shape in code:

- service build/deploy settings live in:
  - `frontend/railway.toml`
  - `backend/railway.toml`
  - `mcp_server/railway.toml`
- project bootstrap and variable wiring live in:
  - `scripts/railway-deploy.ps1`

Railway template publication itself is still a dashboard action, so this file is the source-controlled blueprint for the template composer.

## Services

- `connexity-fe`
  - source repo root directory: `/frontend`
  - public networking: enabled
  - healthcheck: `/api/health`
- `connexity-be`
  - source repo root directory: `/backend`
  - private networking only
  - healthcheck: `/`
- `connexity-mcp`
  - source repo root directory: `/mcp_server`
  - public networking: enabled
  - healthcheck: `/healthz`
- `Postgres`
  - Railway managed PostgreSQL

## Shared template inputs

These should be entered once in the template UI and referenced into services:

- `JWT_SECRET_KEY`
- `ENCRYPTION_KEY`
- `MCP_CLIENT_SECRET`
- `OPENAI_API_KEY` if OpenAI-backed features are needed
- `ANTHROPIC_API_KEY` if Anthropic-backed features are needed

Recommended generation:

- `JWT_SECRET_KEY = ${{ secret(64) }}`
- `MCP_CLIENT_SECRET = ${{ secret(64) }}`
- optional `MCP_CLIENT_ID = custom-mcp-client`

`ENCRYPTION_KEY` cannot safely use a plain `secret()` value because the backend validates it as a Fernet key.

## Service variables

`connexity-fe`

- `API_URL = http://${{ connexity-be.RAILWAY_PRIVATE_DOMAIN }}:${{ connexity-be.PORT }}`

`connexity-be`

- `DATABASE_URL = ${{ Postgres.DATABASE_URL }}`
- `PORT = 8000`
- `ENVIRONMENT = production`
- `JWT_SECRET_KEY = ${{ shared.JWT_SECRET_KEY }}`
- `ENCRYPTION_KEY = ${{ shared.ENCRYPTION_KEY }}`
- `MCP_CLIENT_SECRET = ${{ shared.MCP_CLIENT_SECRET }}`
- optional `MCP_CLIENT_ID = ${{ shared.MCP_CLIENT_ID }}`
- `OPENAI_API_KEY = ${{ shared.OPENAI_API_KEY }}` if used
- `ANTHROPIC_API_KEY = ${{ shared.ANTHROPIC_API_KEY }}` if used

`connexity-mcp`

- `CONNEXITY_API_URL = http://${{ connexity-be.RAILWAY_PRIVATE_DOMAIN }}:${{ connexity-be.PORT }}/api/v1`
- `MCP_CLIENT_SECRET = ${{ shared.MCP_CLIENT_SECRET }}`
- optional `MCP_CLIENT_ID = ${{ shared.MCP_CLIENT_ID }}`

## MCP auth

MCP-to-backend auth is a shared-secret exchange:

- backend `MCP_CLIENT_SECRET`
- mcp `MCP_CLIENT_SECRET`
- optional override on both sides: `MCP_CLIENT_ID`

The MCP service exchanges those values for a short-lived backend JWT at
`/api/v1/internal/token`. Do not use CLI credentials or user email/password
credentials in the template. If `MCP_CLIENT_ID` is omitted, both services use
the built-in `mcp-server` identity.
