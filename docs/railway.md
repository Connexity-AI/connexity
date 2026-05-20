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
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `CONNEXITY_API_TOKEN`
- `CONNEXITY_EMAIL`
- `CONNEXITY_PASSWORD`

`ENCRYPTION_KEY` must be a valid Fernet key. Generate one with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

These values should be reference variables, not hard-coded strings:

- `frontend.SITE_URL`
- `backend.SITE_URL`
- `frontend.API_URL`
- `mcp-server.CONNEXITY_API_URL`

The recommended pattern is:

- `SITE_URL=https://${{ frontend.RAILWAY_PUBLIC_DOMAIN }}`
- `API_URL=http://${{ backend.RAILWAY_PRIVATE_DOMAIN }}:8000/api/v1`
- `CONNEXITY_API_URL=http://${{ backend.RAILWAY_PRIVATE_DOMAIN }}:8000/api/v1`

That keeps the browser-facing URL public while keeping backend-to-backend traffic on Railway's private network.

## Health checks

The frontend exposes a dedicated `/api/health` route so Railway can wait for a real `200` before marking a deployment healthy. The backend and MCP server already expose `/` and `/healthz` respectively.

## Security

For extra protection, seal secret variables in Railway after they are created. Sealed values are available to builds and deployments but are not visible in the UI or retrievable through the API.

## Template note

The repository is ready for a Railway template, but publishing the reusable template still happens in Railway's dashboard. CLI can bootstrap and deploy the project; the template publish step is a Railway UI action.
