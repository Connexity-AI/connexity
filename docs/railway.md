# Railway deployment

Connexity is structured so Railway can host the full stack as separate services:

- `frontend`
- `backend`
- `Postgres`
- optional `mcp-server`

Each deployable service has its own `railway.toml` alongside the code it runs:

- `frontend/railway.toml`
- `backend/railway.toml`
- `mcp_server/railway.toml`

## CLI-first workflow

Use the Railway CLI to create and populate the project:

```powershell
./scripts/railway-deploy.ps1
```

The script:

1. Creates or links the Railway project.
2. Adds PostgreSQL.
3. Adds the frontend, backend, and optional MCP services.
4. Uses Railway reference variables so service URLs stay in sync.
5. Deploys each service from its own subdirectory.

## Railway setup

Railway still needs one service per deployable component. The `railway.toml` files keep each service's build and deploy settings in git, but you still set the service root directory in Railway to:

- `/frontend`
- `/backend`
- `/mcp_server`

Once that is done, Railway will read the config file from each service directory and apply it on deploy.

## Variables

These values should be treated as secrets:

- `JWT_SECRET_KEY`
- `ENCRYPTION_KEY`
- `MCP_CLIENT_SECRET`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

`ENCRYPTION_KEY` must be a valid Fernet key. Generate one with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

These values should be reference variables or coordinated service variables, not hard-coded strings:

- `backend.PORT`
- `frontend.API_URL`
- `mcp-server.CONNEXITY_API_URL`

The recommended pattern is:

- `PORT=8000` on the backend service
- `API_URL=http://${{ backend.RAILWAY_PRIVATE_DOMAIN }}:${{ backend.PORT }}`
- `CONNEXITY_API_URL=http://${{ backend.RAILWAY_PRIVATE_DOMAIN }}:${{ backend.PORT }}/api/v1`
- `MCP_CLIENT_SECRET=<long random secret>` shared into:
  - `backend.MCP_CLIENT_SECRET`
  - `mcp-server.MCP_CLIENT_SECRET`
- optional `MCP_CLIENT_ID=<custom service id>` shared into:
  - `backend.MCP_CLIENT_ID`
  - `mcp-server.MCP_CLIENT_ID`
  - if omitted, both services default to `mcp-server`

The frontend now derives its own public base URL from `RAILWAY_PUBLIC_DOMAIN`, and the backend derives the same public URL from `RAILWAY_SERVICE_CONNEXITY_FE_URL` when `SITE_URL` is unset. The MCP server likewise derives its public base URL from `RAILWAY_PUBLIC_DOMAIN` when `MCP_PUBLIC_BASE_URL` is unset.

For Railway production deployments, the intended and only supported MCP auth path is:

- MCP server sends `MCP_CLIENT_ID` and `MCP_CLIENT_SECRET` to `POST /api/v1/internal/token`
- backend compares those values to its configured values; `MCP_CLIENT_ID` defaults to `mcp-server`
- backend returns a short-lived service JWT
- MCP server uses that JWT for `/api/v1/mcp/*` requests

The frontend expects the backend origin only because its generated client already prefixes routes with `/api/v1`. The MCP server accepts either form, but using the explicit `/api/v1` URL keeps it aligned with the backend CLI defaults.

Railway injects a runtime `PORT`, but private-network callers still need to know which port the backend listens on. Setting `backend.PORT` yourself keeps the backend listener and the URLs used by the frontend and MCP server in sync.

That keeps the browser-facing URL public while keeping backend-to-backend traffic on Railway's private network.

## Health checks

The frontend exposes a dedicated `/api/health` route so Railway can wait for a real `200` before marking a deployment healthy. The backend and MCP server already expose `/` and `/healthz` respectively.

## Security

For extra protection, seal secret variables in Railway after they are created. Sealed values are available to builds and deployments but are not visible in the UI or retrievable through the API.

## Template note

The repository is ready for a Railway template, but publishing the reusable template still happens in Railway's dashboard. CLI can bootstrap and deploy the project; the template publish step is a Railway UI action.
