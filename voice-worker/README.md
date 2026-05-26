# Voice runner (`voice-worker`)

Local **Pipecat 1.2.1 + Twilio** caller worker for Connexity voice simulations. It claims `voice_simulation_job` rows from Postgres, places an outbound call, streams audio over Twilio Media Streams (`/twiml/{job_id}` + websocket `/ws`), injects framed DTMF after the callee’s **first finalized STT transcription**, drives the evaluator persona (`app.services.user_simulator` prompt wiring), hangs up after `max_call_duration_seconds`, and moves jobs to **`waiting_for_result`** for user-side submissions.

## Local process (development)

```bash
cd voice-worker

# Loads ../.env alongside backend variables (DATABASE_URL / POSTGRES_*, TWILIO_*, speech keys).
export VOICE_PUBLIC_BASE_URL="https://<your-ngrok-host>"   # no trailing slash

uv sync
uv run python -m voice_runner
```

The HTTP listener defaults to `0.0.0.0:8765`; override via `VOICE_WORKER_HTTP_HOST` / `VOICE_WORKER_HTTP_PORT`.

## Docker Compose (voice mode)

Text-only `docker compose up` is unchanged. Voice mode adds the worker and an ffmpeg-enabled backend image:

```bash
cp .env.example .env
# Set TWILIO_* credentials, speech provider keys, POSTGRES_PASSWORD, and:
#   VOICE_PUBLIC_BASE_URL=https://<public-host>   # ngrok or similar — no trailing slash

docker compose -f docker-compose.yml -f docker-compose.voice.yml -f docker-compose.voice.build.yml up --build
```

To build the frontend locally as well, add `docker-compose.build.yml` to the `-f` list.

Services added by `docker-compose.voice.yml` (build via `docker-compose.voice.build.yml`):

| Service | Role |
|---|---|
| `voice-worker` | Claims jobs, dials Twilio, serves TwiML + Media Stream WebSocket |
| `backend` (override) | Rebuilt with `Dockerfile.voice` so submitted recordings can be normalized via **ffmpeg** for DTMf decoding |

`VOICE_DEPLOYMENT_MODE=local` is set by Compose (not user `.env`). Only **one** voice-worker replica runs by default — one active call per process.

### Public URL for Twilio

Twilio must reach the worker over HTTPS for outbound-call TwiML and the bidirectional Media Stream WebSocket. For local development:

1. Start the voice stack (or `uv run python -m voice_runner` against the same Postgres).
2. Tunnel port **8765** with [ngrok](https://ngrok.com/) (or Cloudflare Tunnel, etc.).
3. Set `VOICE_PUBLIC_BASE_URL` to the tunnel origin, e.g. `https://abc123.ngrok-free.app` (no path, no trailing slash).
4. Point Twilio at that origin indirectly — the worker dials with a webhook URL derived from `VOICE_PUBLIC_BASE_URL/twiml/{job_id}`.

The backend API (`SITE_URL` / port 8000) remains separate; user agents submit results to the Connexity backend, not the voice worker.

### Mock voice agent (local E2E)

To test the full voice loop (call → DTMF → result submission → judge), run [examples/mock-voice-agent/](../examples/mock-voice-agent/) on port **8766**, point a Twilio number at its `/incoming` webhook, and use that number as the agent phone number in a voice eval config.

## Tests

```bash
cd voice-worker
uv run pytest tests -v
```

## Scope & limitations

- Simulator **scripted** mode is rejected for now (`ValueError`).
- Gemini LLM needs `GOOGLE_GENAI_API_KEY` or `GOOGLE_API_KEY` in `.env`.
- Kubernetes one-shot worker mode is planned separately (see implementation plan step 12).
