# Kubernetes

Use Kubernetes when you want a production install with managed ingress/TLS, separate app components, and optional voice-worker autoscaling. For a simple single-node install, start with [Docker Compose](./docker-compose.md).

The Helm chart lives in [`deploy/helm/connexity`](../../deploy/helm/connexity/README.md). It runs the backend, frontend, migrations, optional bundled Postgres, optional MCP server, and optional voice workers.

## Prerequisites

- Kubernetes 1.25+
- Helm 3.10+
- An ingress controller, such as nginx
- Public DNS for the app and API hosts
- TLS for the app and API hosts

Add the Helm repositories once:

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

KEDA is only required when `voice.enabled=true`:

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda --namespace keda --create-namespace
```

## Demo Install

This profile uses the bundled Postgres chart and creates a demo Secret from Helm values. Use it for quick cluster smoke tests, not production secrets.

```bash
cd deploy/helm/connexity
helm dependency update .

helm upgrade --install connexity . \
  --namespace connexity \
  --create-namespace \
  --set secret.create=true \
  --set postgresql.auth.password='change-me-db-password' \
  --set secret.jwtSecretKey="$(openssl rand -hex 32)" \
  --set secret.encryptionKey="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  --set global.siteUrl=https://app.example.com \
  --set global.apiPublicUrl=https://api.example.com \
  --set ingress.appHost=app.example.com \
  --set ingress.apiHost=api.example.com
```

Check the install:

```bash
kubectl -n connexity get pods,svc,ingress,jobs
kubectl -n connexity logs job/connexity-migrate
```

## Production Install

Production installs should use your own Secret and, usually, an external Postgres database.

1. Create the namespace:

   ```bash
   kubectl create namespace connexity --dry-run=client -o yaml | kubectl apply -f -
   ```

2. Create the app Secret:

   ```bash
   kubectl -n connexity create secret generic connexity-secrets \
     --from-literal=POSTGRES_SERVER='postgres.example.com' \
     --from-literal=POSTGRES_PORT='5432' \
     --from-literal=POSTGRES_USER='connexity' \
     --from-literal=POSTGRES_PASSWORD='replace-with-db-password' \
     --from-literal=POSTGRES_DB='app' \
     --from-literal=JWT_SECRET_KEY="$(openssl rand -hex 32)" \
     --from-literal=ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
     --from-literal=OPENAI_API_KEY='replace-if-used' \
     --from-literal=TWILIO_ACCOUNT_SID='ACxxxxxxxx' \
     --from-literal=TWILIO_AUTH_TOKEN='replace-if-using-voice' \
     --from-literal=TWILIO_FROM_NUMBER='+15551234567' \
     --from-literal=DEEPGRAM_API_KEY='replace-if-used' \
     --from-literal=ELEVENLABS_API_KEY='replace-if-used' \
     --from-literal=CARTESIA_API_KEY='replace-if-used' \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

   Remove optional keys you do not use, and add any other model provider keys your evals need, such as `ANTHROPIC_API_KEY` or `GOOGLE_API_KEY`.

3. Create the TLS Secret, unless cert-manager or your ingress setup creates it for you:

   ```bash
   kubectl -n connexity create secret tls connexity-tls \
     --cert=/path/to/tls.crt \
     --key=/path/to/tls.key \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

4. Create `values-production.yaml`:

   ```bash
   cat > values-production.yaml <<'EOF'
   postgresql:
     enabled: false

   externalDatabase:
     host: postgres.example.com
     port: 5432
     user: connexity
     password: "" # stored in connexity-secrets
     database: app

   secret:
     create: false
     existingSecret: connexity-secrets

   global:
     siteUrl: https://app.example.com
     apiPublicUrl: https://api.example.com

   ingress:
     enabled: true
     className: nginx
     appHost: app.example.com
     apiHost: api.example.com
     tls:
       enabled: true
       secretName: connexity-tls
   EOF
   ```

5. Install or upgrade:

   ```bash
   cd deploy/helm/connexity
   helm dependency update .

   helm upgrade --install connexity . \
     --namespace connexity \
     -f values-production.yaml
   ```

6. Verify:

   ```bash
   kubectl -n connexity get pods,svc,ingress,jobs
   kubectl -n connexity logs job/connexity-migrate
   kubectl -n connexity rollout status deploy/connexity-backend
   kubectl -n connexity rollout status deploy/connexity-frontend
   ```

## Voice Mode

Voice mode is optional. Text-only evaluation does not need Twilio, speech keys, KEDA, wildcard DNS, or voice workers.

1. Make sure `connexity-secrets` includes `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, and the speech provider keys used by your eval configs.

2. Add voice values to `values-production.yaml`:

   ```yaml
   voice:
     enabled: true
     maxConcurrency: 5
     publicHostSuffix: voice.example.com
     ingress:
       tls:
         secretName: connexity-voice-tls

   backend:
     image:
       useVoiceVariant: true
       voiceTag: latest
   ```

3. Point wildcard DNS at the ingress load balancer:

   ```text
   *.voice.example.com -> your ingress load balancer
   ```

4. Create the wildcard TLS Secret, unless cert-manager or your ingress setup creates it for you:

   ```bash
   kubectl -n connexity create secret tls connexity-voice-tls \
     --cert=/path/to/wildcard-voice.crt \
     --key=/path/to/wildcard-voice.key \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

5. Upgrade:

   ```bash
   helm upgrade --install connexity deploy/helm/connexity \
     --namespace connexity \
     -f values-production.yaml
   ```

6. Verify the scaler and workers:

   ```bash
   kubectl -n connexity get scaledobject,triggerauthentication
   kubectl -n connexity get statefulset,pods -l app.kubernetes.io/component=voice-worker
   ```

## MCP Server

The MCP server is disabled by default. Add this to `values-production.yaml` to enable it:

```yaml
mcp:
  enabled: true
  ingress:
    host: mcp.example.com
  env:
    mcpPublicBaseUrl: https://mcp.example.com
    mcpOauthIssuerUrl: https://api.example.com
    mcpOauthAudience: https://mcp.example.com/mcp
```

Then upgrade:

```bash
helm upgrade --install connexity deploy/helm/connexity \
  --namespace connexity \
  -f values-production.yaml
```
