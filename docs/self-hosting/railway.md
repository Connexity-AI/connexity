# Railway deployment

Connexity can run on Railway as a small multi-service project: frontend, backend,
MCP server, and Postgres. This guide focuses on the environment variables that
matter for a working template and explains how MCP authentication is wired.

## Services

A typical Railway project has these services:

- `frontend` for the web app
- `backend` for the API, auth, and core application logic
- `mcp` for the standalone MCP transport
- `postgres` for the database

## Template inputs

Recommended template behavior:

- prefill `ENVIRONMENT=production`
- auto-generate `JWT_SECRET_KEY`
- auto-generate `ENCRYPTION_KEY`
- require at least one LLM provider key such as `OPENAI_API_KEY`

For Railway templates, these values work well:

```text
ENVIRONMENT=production
JWT_SECRET_KEY=${{ secret(64, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_") }}
ENCRYPTION_KEY=${{ secret(43, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_") }}=
```

`JWT_SECRET_KEY` signs browser auth tokens and also seeds the backend's OAuth
signing key. `ENCRYPTION_KEY` must be a valid Fernet key because the backend
uses it to encrypt stored integration secrets.

## Backend setup

The backend needs:

- database connection settings
- `JWT_SECRET_KEY`
- `ENCRYPTION_KEY`
- at least one LLM provider key

Useful notes from the runtime config:

- `SITE_URL` is optional on Railway if the frontend service public domain is
  available to the backend environment.
- `OAUTH_ISSUER_URL` is optional if the backend itself has a Railway public
  domain; it falls back to `https://${RAILWAY_PUBLIC_DOMAIN}`.
- the backend must know the MCP OAuth audience. Set either
  `OAUTH_DEFAULT_RESOURCE_URL` or `MCP_OAUTH_AUDIENCE` to the public MCP URL,
  usually `https://<your-mcp-domain>/mcp`.

Example backend values:

```text
ENVIRONMENT=production
OAUTH_DEFAULT_RESOURCE_URL=https://<your-mcp-domain>/mcp
```

## MCP setup

The MCP service must know:

- where the backend API lives
- the public MCP URL Claude will connect to
- which OAuth issuer should mint and validate MCP access tokens

Set these on the MCP service:

```text
CONNEXITY_API_URL=https://<your-backend-domain>/api/v1
MCP_PUBLIC_BASE_URL=https://<your-mcp-domain>
MCP_OAUTH_ISSUER_URL=https://<your-backend-domain>
```

Optional MCP variables:

- `MCP_PATH` defaults to `/mcp`
- `MCP_OAUTH_AUDIENCE` defaults to `${MCP_PUBLIC_BASE_URL}${MCP_PATH}`
- `MCP_OAUTH_REQUIRED_SCOPES` defaults to `mcp:access`
- `MCP_OAUTH_RESOURCE_SERVER_URL` defaults to `${MCP_PUBLIC_BASE_URL}${MCP_PATH}`

## How MCP auth works

Connexity uses OAuth for MCP transport. The MCP service is not anonymous.

The flow is:

1. The user pastes the public MCP URL into Claude.
2. Claude reads the MCP resource metadata and discovers that OAuth is required.
3. Claude registers itself through the backend's Dynamic Client Registration
   endpoint.
4. The user is redirected to the backend sign-in or sign-up flow.
5. The backend issues an OAuth access token for the MCP audience, typically
   `https://<your-mcp-domain>/mcp`, with the `mcp:access` scope.
6. Claude calls the MCP server with that bearer token.
7. The MCP server forwards the authenticated user's token to the backend for
   `/api/v1/mcp/*` requests.
8. The backend validates the token's signature, issuer, audience, scope, and
   user identity before allowing MCP actions.

In practical terms:

- the backend is the OAuth issuer
- the MCP service is the OAuth-protected resource server
- the MCP token represents a real Connexity user
- agent and workspace actions remain scoped by Connexity's backend rules

## What users need to enter

For a good Railway template UX, ask users only for values that cannot be safely
derived or generated:

- `OPENAI_API_KEY` or another provider key
- any optional SMTP settings they plan to use
- any custom `SITE_URL` or custom domain overrides if they are not relying on
  Railway defaults

Do not ask users to hand-generate:

- `ENVIRONMENT`
- `JWT_SECRET_KEY`
- `ENCRYPTION_KEY`

## First connection test

After deploy:

1. Open the frontend and create an account.
2. Confirm the backend is reachable on its public domain.
3. Confirm the MCP service is reachable at `https://<your-mcp-domain>/mcp`.
4. Paste that MCP URL into Claude.
5. Complete the sign-in flow and confirm Claude can list or access MCP tools.

If Claude reaches the MCP URL but auth fails, check these first:

- backend `OAUTH_DEFAULT_RESOURCE_URL` or `MCP_OAUTH_AUDIENCE`
- MCP `MCP_PUBLIC_BASE_URL`
- MCP `MCP_OAUTH_ISSUER_URL`
- that backend and MCP public domains are HTTPS and match the configured values
