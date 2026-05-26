# Connexity platform (Kubernetes / Helm)

Single Helm chart for self-hosting Connexity: backend, frontend, optional bundled Postgres, optional MCP server, and optional voice worker with KEDA autoscaling.

Text-only installs leave `voice.enabled=false` (default). Voice mode adds a StatefulSet, per-pod Ingress hosts, and Twilio routing via `worker_public_base_url`.

## Architecture

```text
Ingress (app) ──► frontend ──► backend ──► Postgres
Ingress (api) ──► backend
Migration Job (Helm hook) ──► Postgres
Ingress (mcp) ──► MCP ──► backend API
Ingress (voice-*) ──► ordinal Services ──► voice worker pods
KEDA ScaledObject ──► voice StatefulSet (scales from job queue)
Twilio ──► per-pod worker URL stored on each voice job
```

## Prerequisites

- Kubernetes 1.25+
- Helm 3.10+
- Ingress controller (nginx recommended)
- TLS certificates for app/API hosts (and `*.voice.example.com` when voice is enabled)
- **KEDA** (required when `voice.enabled=true`):
  ```bash
  helm install keda kedacore/keda --namespace keda --create-namespace
  ```

## Quick start (demo profile)

Bundled Postgres, chart-managed Secret, text-only platform:

```bash
cd deploy/helm/connexity
helm dependency update .

helm upgrade --install connexity . \
  --namespace connexity \
  --create-namespace \
  --set secret.create=true \
  --set postgresql.auth.password=demo-password \
  --set secret.jwtSecretKey="$(openssl rand -hex 32)" \
  --set secret.encryptionKey="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  --set global.siteUrl=https://app.example.com \
  --set global.apiPublicUrl=https://api.example.com \
  --set ingress.appHost=app.example.com \
  --set ingress.apiHost=api.example.com
```

Point DNS for `app.example.com` and `api.example.com` at your Ingress load balancer. Create TLS secret `connexity-tls` (or use cert-manager).

When `secret.create=true`, the chart renders normalized `POSTGRES_*` keys using the bundled Postgres service name (`{release}-postgresql`).

## Production profile (external database)

```yaml
# values-production.yaml
postgresql:
  enabled: false

externalDatabase:
  host: postgres.example.com
  port: 5432
  user: connexity
  password: "" # use existingSecret instead
  database: app

secret:
  create: false
  existingSecret: connexity-secrets

global:
  siteUrl: https://app.example.com
  apiPublicUrl: https://api.example.com

ingress:
  appHost: app.example.com
  apiHost: api.example.com
  tls:
    secretName: connexity-tls
```

Create [`secret.example.yaml`](./secret.example.yaml) with `POSTGRES_*`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, LLM keys, and optional Twilio/speech keys before install.

```bash
kubectl apply -f connexity-secrets.yaml
helm upgrade --install connexity . -f values-production.yaml
```

For Neon or other managed Postgres, the backend can use `DATABASE_URL`, but the Helm chart and KEDA scaler still need discrete `externalDatabase.host`, `externalDatabase.port`, `externalDatabase.user`, `externalDatabase.password`, and `externalDatabase.database` values when `voice.enabled=true`.

## Voice simulations

Enable voice worker scaling and backend kubernetes mode:

```yaml
voice:
  enabled: true
  maxConcurrency: 5
  publicHostSuffix: voice.example.com

backend:
  image:
    useVoiceVariant: true  # ffmpeg-enabled backend image for DTMF decode
```

Requirements:

1. **Wildcard DNS** — `*.voice.example.com` → Ingress LB.
2. **Wildcard TLS** — secret referenced by `voice.ingress.tls.secretName`.
3. **Twilio + speech keys** in the shared Secret (`TWILIO_*`, `DEEPGRAM_API_KEY`, etc.).
4. **Backend ffmpeg image** — build from [`backend/Dockerfile.voice`](../../../backend/Dockerfile.voice) and set `backend.image.voiceTag` if your registry uses a separate tag.
5. **KEDA** installed in the cluster.

The chart sets `VOICE_DEPLOYMENT_MODE=kubernetes` and `VOICE_MAX_CONCURRENCY` on the backend automatically. Keep `voice.maxConcurrency` aligned with backend enforcement.

Per-pod worker URLs look like:

```text
https://{release}-connexity-voice-worker-0.voice.example.com
https://{release}-connexity-voice-worker-1.voice.example.com
...
```

Each claimed job stores its `worker_public_base_url` before dialing so Twilio hits the correct pod.

## MCP server (optional)

```yaml
mcp:
  enabled: true
  env:
    mcpPublicBaseUrl: https://mcp.example.com
    mcpOauthIssuerUrl: https://api.example.com
    mcpOauthAudience: https://mcp.example.com/mcp
```

MCP transport requires OAuth resource-server settings at startup. The backend must expose OAuth at `OAUTH_ISSUER_URL` (set from `global.apiPublicUrl`).

## Local smoke test with kind

Minimal cluster validation without real DNS/TLS:

```bash
kind create cluster --name connexity-smoke

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace

cd deploy/helm/connexity
helm dependency update .

helm upgrade --install connexity . \
  --namespace connexity --create-namespace \
  --set secret.create=true \
  --set postgresql.auth.password=smoke \
  --set secret.jwtSecretKey=smoke-jwt-secret-change-me-in-prod \
  --set secret.encryptionKey="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  --set ingress.enabled=false

kubectl -n connexity wait --for=condition=complete job/connexity-migrate --timeout=300s
kubectl -n connexity port-forward svc/connexity-frontend 3000:3000
kubectl -n connexity port-forward svc/connexity-backend 8000:8000
```

Open http://localhost:3000 (frontend proxies API through in-cluster `API_URL`).

To smoke voice scaling templates (requires KEDA):

```bash
helm upgrade connexity . --reuse-values \
  --set voice.enabled=true \
  --set ingress.enabled=false \
  --set voice.ingress.enabled=false
helm template connexity . --set voice.enabled=true | kubectl apply -f -
```

Use real DNS/TLS and Twilio credentials for end-to-end voice eval runs.

## Migrations

Alembic migrations run in a Helm hook Job (`connexity-migrate`) on install/upgrade. Backend pods use `RUN_DB_PRESTART=0` so replicas do not race migrations.

## Values reference

| Value | Purpose |
|---|---|
| `secret.existingSecret` | Kubernetes Secret with normalized app env keys |
| `secret.create` | Render demo Secret from chart values |
| `postgresql.enabled` | Bundled Bitnami Postgres subchart |
| `externalDatabase.*` | External Postgres when bundled DB is disabled |
| `global.siteUrl` / `global.apiPublicUrl` | Public URLs for frontend/backend OAuth |
| `ingress.appHost` / `ingress.apiHost` | Ingress hostnames |
| `voice.enabled` | Voice worker StatefulSet + KEDA |
| `voice.maxConcurrency` | Max replicas and ordinal Ingress rules |
| `voice.publicHostSuffix` | DNS suffix for per-pod worker hosts |
| `mcp.enabled` | MCP server Deployment |

## Validation

```bash
cd deploy/helm/connexity
helm dependency update .
helm lint .
helm template connexity . --set secret.create=true > /tmp/connexity-default.yaml
helm template connexity . --set secret.create=true --set voice.enabled=true > /tmp/connexity-voice.yaml
helm template connexity . --set secret.create=true --set mcp.enabled=true > /tmp/connexity-mcp.yaml
helm template connexity . --set secret.create=true --set postgresql.enabled=false \
  --set externalDatabase.host=db.example.com --set externalDatabase.password=x > /tmp/connexity-extdb.yaml
```

## Related docs

- Kubernetes self-hosting guide: [`docs/self-hosting/kubernetes.md`](../../../docs/self-hosting/kubernetes.md)
- Docker Compose self-hosting: [`docs/self-hosting/docker-compose.md`](../../../docs/self-hosting/docker-compose.md)
- Voice worker runtime: [`voice-worker/README.md`](../../../voice-worker/README.md)
- Voice agent contract: [`docs/voice-agent-contract.md`](../../../docs/voice-agent-contract.md)
- Mock voice agent E2E: [`examples/mock-voice-agent/README.md`](../../../examples/mock-voice-agent/README.md)
