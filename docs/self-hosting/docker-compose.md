# VM deployment (Docker Compose)

Connexity ships a **Docker Compose** stack that runs the frontend, backend, Postgres, migrations, and a small database UI. That same stack runs on **your laptop** or on a **cloud VM**.

This mirrors the usual self-hosted pattern documented for other Compose-based products (compare [Langfuse: Docker Compose on local or VM](https://langfuse.com/self-hosting/deployment/docker-compose)): clone the repo, set secrets, expose the web port.

## Prerequisites

You need **`git`**, **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (macOS / Windows) or **[Docker Engine on Linux](https://docs.docker.com/engine/install/)**, and the **Compose plugin**.

## Local (already on your machine)

1. Clone the repository and enter the directory.
2. Copy `.env.example` to `.env` and set **`SITE_URL`**, **`JWT_SECRET_KEY`**, **`ENCRYPTION_KEY`**, **`POSTGRES_PASSWORD`**, plus **at least one LLM provider key** your deployment will use (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or others referenced in [.env.example](../../.env.example)).
3. Start the stack:

   ```bash
   docker compose up
   ```

4. Open **`http://localhost:3000`** (or **`SITE_URL`**) when the services are healthy, create an account, and sign in.

## Virtual machine

Use this when deploying on AWS, GCP, Azure, or any provider that offers VMs.

### 1. Provision and SSH

- Create a VM (Ubuntu LTS works well).
- Prefer **multiple vCPUs and enough RAM** for Postgres + frontend + backend.
- Give the instance enough **disk** for Postgres.
- Attach a **public IP** only if browsers or external clients must reach the UI without VPN or tunnel.

### 2. Install Docker and Compose

Follow the **[official Docker docs for Ubuntu](https://docs.docker.com/engine/install/ubuntu/)**, then install **`docker-ce`**, **`containerd.io`**, and **`docker-compose-plugin`**. Confirm with:

```bash
sudo docker run hello-world
```

### 3. Clone and configure

```bash
git clone https://github.com/Connexity-AI/connexity.git
cd connexity
cp .env.example .env
```

Edit **`.env`**: matching production **`SITE_URL`** (often `https://…`), secrets, Postgres password, and **LLM API keys**.

### 4. Firewall and ports

Typically you expose **HTTPS** via a reverse proxy to the frontend (recommended for production).

For evaluation only, operators often expose **TCP 3000** (UI) behind a restrictive security group.

### 5. Run

```bash
docker compose up
```

Open **`SITE_URL`** in the browser (or **`http://<instance-ip>:3000`** for a minimal test).

## Voice mode

Text evaluation uses the default Compose stack. To run voice evaluations locally, add the voice Compose files and expose the voice worker through a public HTTPS URL that Twilio can reach.

1. Start a tunnel to the voice worker port:

   ```bash
   ngrok http 8765
   ```

2. Set the required voice values in `.env`:

   ```bash
   TWILIO_ACCOUNT_SID=ACxxxxxxxx
   TWILIO_AUTH_TOKEN=your-token
   TWILIO_FROM_NUMBER=+15551234567

   # Use the https:// forwarding URL from ngrok.
   VOICE_PUBLIC_BASE_URL=https://your-worker-url.ngrok-free.app

   # Configure the speech providers used by your voice evals.
   DEEPGRAM_API_KEY=...
   ELEVENLABS_API_KEY=...
   OPENAI_API_KEY=...
   ```

3. Start the stack with local voice images:

   ```bash
   docker compose \
     -f docker-compose.yml \
     -f docker-compose.build.yml \
     -f docker-compose.voice.yml \
     -f docker-compose.voice.build.yml \
     up --build
   ```

4. Open the app at `SITE_URL`, create or select a voice eval config, and use a Twilio-reachable agent phone number.

For production voice-worker autoscaling, use the [Kubernetes guide](./kubernetes.md).

### Operational notes

- Compose is suited to **single-node** deployments and **vertical scaling**. It is not HA by itself.
- For shutdown: **Ctrl+C** in the foreground, or **`docker compose down`** if you ran with **`docker compose up -d`** (add **`docker compose down -v`** to remove volumes too).

For local development outside Docker—Postgres still in Compose, apps on the host—see [CONTRIBUTING.md](../../CONTRIBUTING.md).
