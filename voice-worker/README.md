# Voice runner (`voice-worker`)

Local **Pipecat 1.2.1 + Twilio** caller worker for Connexity voice simulations. It claims `voice_simulation_job` rows from Postgres, places an outbound call, streams audio over Twilio Media Streams (`/twiml/{job_id}` + websocket `/ws`), injects framed DTMF after the callee’s **first finalized STT transcription**, drives the evaluator persona (`app.services.user_simulator` prompt wiring), hangs up after `max_call_duration_seconds`, and moves jobs to **`waiting_for_result`** for user-side submissions.

```bash
cd voice-worker

# Loads ../.env alongside backend variables (DATABASE_URL / POSTGRES_*, TWILIO_*, speech keys).
export VOICE_PUBLIC_BASE_URL="https://<your-ngrok-host>" # no trailing slash

uv sync

uv run python -m voice_runner
```

The HTTP listener defaults to `0.0.0.0:8765`; override via `VOICE_WORKER_HTTP_HOST` / `VOICE_WORKER_HTTP_PORT`.

## Scope & limitations

- Simulator **scripted** mode is rejected for now (`ValueError`).
- Gemini LLM needs `GOOGLE_GENAI_API_KEY` or `GOOGLE_API_KEY` in `.env`.

See `docs/voice-simulations-implementation-plan.md` step 10 for Compose wiring next.
