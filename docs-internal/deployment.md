# Deployment

How code on `main` reaches production. Set up on 2026-11-12 (Decided by Dmytro: Google
Cloud Run, connected to this repository).

## What runs where

Google Cloud project `connexity-490409`, region `europe-west1` (next to the database).

| Service | Built from | What it is |
|---|---|---|
| `connexity-backend` | `backend/Dockerfile` | The API. Runs the migrations on every start (`scripts/entrypoint.sh`). |
| `connexity-ui` | `frontend/Dockerfile` | The web app. |
| `connexity-mcp` | `mcp_server/Dockerfile` | The MCP server the user's assistant connects to, at `https://mcp.connexity.ai/mcp`. Public, protected by OAuth that the backend issues or a personal access token. |

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

## Addresses

| Address | Service | How |
|---|---|---|
| `app.connexity.ai` | `connexity-ui` | Cloud Run domain mapping |
| `mcp.connexity.ai` | `connexity-mcp` | Cloud Run domain mapping (2026-11-13) |
| `api.connexity.ai` | `connexity-backend` | Cloud Run domain mapping (2026-11-13) |

Each needs a DNS record in Cloudflare, `CNAME` to `ghs.googlehosted.com`, **DNS only**
(not proxied), or the certificate is never issued. The backend's address,
`https://api.connexity.ai`, is also the OAuth issuer (`OAUTH_ISSUER_URL`); webhook
addresses are built from it.

The MCP address assistants use is `https://mcp.connexity.ai/mcp`: `MCP_PUBLIC_BASE_URL`
is `https://mcp.connexity.ai` and `MCP_OAUTH_AUDIENCE` (on both services) is
`https://mcp.connexity.ai/mcp`. Changing the audience makes every OAuth connection
issued for the old address stop working; those assistants must be connected again.
Personal access tokens do not depend on it.

**Sign in with Google** needs two backend settings: `GOOGLE_CLIENT_ID` (a plain
environment variable) and `GOOGLE_CLIENT_SECRET` (a secret, for example
`connexity-google-client-secret`). Neither is set yet; without both, the Google button
does not appear. The Google OAuth client must list the redirect URI
`<OAUTH_ISSUER_URL>/api/v1/auth/google/callback`, or set `GOOGLE_REDIRECT_URI` to match.

## Things to know

- **Migrations run on start.** A migration that fails stops the new backend revision from
  starting; the old one keeps serving. Fix forward with a new migration.
- **Cloud Run reserves `/healthz`.** Requests to it never reach the MCP container, so do not
  use it for checks; Cloud Run checks that the port is listening.
- **The database starts empty.** The 1.x data was wiped on 2026-11-12 when the rebuild's
  migrations were applied (accepted on 2026-10-06).
- **The scheduled call pull** runs inside Cloud Scheduler's minute requests (see below),
  so the backend needs no instance kept running.

## The scheduled call pull

Cloud Scheduler calls the backend every minute to pull new calls
(`docs-internal/call-ingestion.md`). It is set up once, by hand, with Dmytro's approval:

```bash
gcloud iam service-accounts create connexity-call-pull \
  --project connexity-490409 --display-name "Connexity call pull (Cloud Scheduler)"

gcloud scheduler jobs create http connexity-call-pull \
  --project connexity-490409 --location europe-west1 \
  --schedule "* * * * *" --time-zone "Etc/UTC" \
  --http-method POST \
  --uri https://api.connexity.ai/api/v1/internal/calls/pull \
  --oidc-service-account-email connexity-call-pull@connexity-490409.iam.gserviceaccount.com \
  --oidc-token-audience https://api.connexity.ai/api/v1/internal/calls/pull \
  --attempt-deadline 60s --max-retry-attempts 0

gcloud run services update connexity-backend \
  --project connexity-490409 --region europe-west1 \
  --update-env-vars CALL_PULL_AUDIENCE=https://api.connexity.ai/api/v1/internal/calls/pull,CALL_PULL_INVOKER=connexity-call-pull@connexity-490409.iam.gserviceaccount.com
```

The service account needs no roles: the backend checks its identity itself. Pause the
pull with `gcloud scheduler jobs pause connexity-call-pull --location europe-west1`.
Each run logs a `call_pull` line in the backend's logs.
