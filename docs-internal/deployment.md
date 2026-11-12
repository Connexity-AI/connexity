# Deployment

How code on `main` reaches production. Set up on 2026-11-12 (Decided by Dmytro: Google
Cloud Run, connected to this repository).

## What runs where

Google Cloud project `connexity-490409`, region `europe-west1` (next to the database).

| Service | Built from | What it is |
|---|---|---|
| `connexity-backend` | `backend/Dockerfile` | The API. Runs the migrations on every start (`scripts/entrypoint.sh`). |
| `connexity-ui` | `frontend/Dockerfile` | The web app. |
| `connexity-mcp` | `mcp_server/Dockerfile` | The MCP server the user's assistant connects to. Public, protected by OAuth that the backend issues. |

The database is Supabase (Postgres, session pooler, `eu-west-3`). The backend reads its
address from the `DATABASE_URL` secret.

The project also hosts other products' services; leave them alone.

## How a merge deploys

Each service has a Cloud Build trigger on pushes to `main` that touch its folder:

| Trigger | Fires on |
|---|---|
| backend trigger | `backend/**` |
| frontend trigger | `frontend/**` |
| `connexity-mcp-main` | `mcp_server/**` |

The trigger builds the Dockerfile, pushes the image to Artifact Registry and points the
Cloud Run service at it. A new revision takes traffic only when it starts healthy; a
failing revision leaves the previous one serving. A merge that touches only docs deploys
nothing.

There is no staging environment and no release step: what merges to `main` is live a few
minutes later. GitHub Actions no longer deploy anything (the old SSH deploy workflows
were deleted on 2026-11-12).

## Settings and secrets

Plain settings (URLs) are environment variables on each service. Secrets live in Secret
Manager and are mounted as environment variables; the services' runtime service account
can read them.

| Secret | Used by |
|---|---|
| `connexity-database-url` | backend `DATABASE_URL` |
| `connexity-jwt-secret-key` | backend `JWT_SECRET_KEY` (also derives the OAuth signing key; changing it invalidates every session and MCP token) |
| `connexity-session-secret-key` | backend `SESSION_SECRET_KEY` |
| `connexity-encryption-key` | backend `ENCRYPTION_KEY` (encrypts stored provider keys; changing it makes them unreadable) |
| `connexity-openai-api-key` | backend `OPENAI_API_KEY` |

To change a secret, add a new version (`gcloud secrets versions add <name> --data-file=-`)
and redeploy the service. Never put secret values in this repository or in plain
environment variables.

MCP settings (`CONNEXITY_API_URL`, `MCP_PUBLIC_BASE_URL`, `MCP_OAUTH_ISSUER_URL`,
`MCP_OAUTH_AUDIENCE`) and the backend's `OAUTH_ISSUER_URL` and `MCP_OAUTH_AUDIENCE` point the
services at each other.

## Things to know

- **Migrations run on start.** A migration that fails stops the new backend revision from
  starting; the old one keeps serving. Fix forward with a new migration.
- **Cloud Run reserves `/healthz`.** Requests to it never reach the MCP container, so do not
  use it for checks; Cloud Run checks that the port is listening.
- **The database starts empty.** The 1.x data was wiped on 2026-11-12 when the rebuild's
  migrations were applied (accepted on 2026-10-06).
- **Continuous call sync** will need the backend to keep at least one instance and its CPU
  running; set that when the sync feature ships.
