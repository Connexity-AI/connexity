# Mock voice agent

Lightweight [Pipecat](https://github.com/pipecat-ai/pipecat) + Twilio **inbound** voice agent for testing Connexity voice-mode evals locally. Connexity’s voice worker places an outbound call to your Twilio number; this service answers, runs STT → LLM → TTS, saves a WAV recording (including Connexity’s in-band DTMF tones), and submits `{audio_url, messages}` to Connexity when the call ends.

**Start here for Connexity integration:** [`connexity.py`](./connexity.py) — annotated helpers for the three required touchpoints. Full spec: [voice agent contract](../../docs/voice-agent-contract.md).

For text-mode evals, use [mock-text-agent](../mock-text-agent/) and the [text agent contract](../../docs/text-agent-contract.md).

Pattern adapted from [pipecat-examples/twilio-chatbot/inbound](https://github.com/pipecat-ai/pipecat-examples/tree/main/twilio-chatbot/inbound).

## Prerequisites

- Connexity voice stack running (`docker compose … voice.yml`)
- Twilio account with a **voice-capable phone number**
- Public HTTPS tunnel to this process (ngrok, Cloudflare Tunnel, etc.)
- API keys: `DEEPGRAM_API_KEY`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`
- Connexity bearer token (`CONNEXITY_API_TOKEN`) for result submission

## Quick start

```bash
cd examples/mock-voice-agent
uv sync

# Configure via examples/mock-voice-agent/env.example (repo root `.env` also works)
export MOCK_VOICE_AGENT_PUBLIC_BASE_URL=https://<your-tunnel>
export CONNEXITY_API_URL=http://localhost:8000
export CONNEXITY_API_TOKEN=<jwt from login>
# TWILIO_*, DEEPGRAM_API_KEY, OPENAI_API_KEY, ELEVENLABS_API_KEY

uv run python main.py
```

Default HTTP port is **8766** (voice worker uses 8765).

### 1. Tunnel this service

```bash
ngrok http 8766
```

Set `MOCK_VOICE_AGENT_PUBLIC_BASE_URL` to the ngrok HTTPS origin (no path, no trailing slash).

### 2. Configure Twilio

In the Twilio console, open **Phone Numbers → your agent number → Voice configuration**:

- **A call comes in:** Webhook
- **URL:** `https://<your-tunnel>/incoming`
- **Method:** HTTP POST

Connexity voice eval configs should use this number as **Agent phone number**.

### 3. Run a voice eval

1. Start the Docker voice stack and this mock voice agent.
2. Create a voice eval config pointing at the Twilio number above.
3. Run one test case.
4. After hangup, `connexity.py` POSTs to `POST /api/v1/voice-simulations/results`.

Check run detail in the Connexity UI for DTMF decode status and judged transcript.

## Where Connexity integration lives

| File | Connexity-related code |
|------|------------------------|
| [`connexity.py`](./connexity.py) | **All integration helpers** — recording URL, message export, result POST |
| [`main.py`](./main.py) | Comments at `/recordings` (public `audio_url`) and call-complete hook |
| [`bot.py`](./bot.py) | Comment at call-end handoff to `connexity.py` |
| Everything else | Your agent (Pipecat, Twilio, tools) — swap freely |

## Endpoints

| Path | Purpose |
|------|---------|
| `GET /health` | Liveness |
| `POST /incoming` | Twilio voice webhook → TwiML Media Stream |
| `WS /ws` | Twilio Media Stream (Pipecat pipeline) |
| `GET /recordings/{CallSid}.wav` | **Connexity `audio_url`** — must include DTMF tones |

## Configuration

See [env.example](./env.example).

| Env var | Default | Description |
|---------|---------|-------------|
| `MOCK_VOICE_AGENT_PUBLIC_BASE_URL` | — | Public HTTPS origin for TwiML + recording URLs |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | — | Twilio REST + Media Stream auth |
| `DEEPGRAM_API_KEY` | — | Speech-to-text |
| `OPENAI_API_KEY` | — | LLM |
| `ELEVENLABS_API_KEY` | — | Text-to-speech |
| `CONNEXITY_API_URL` | `http://localhost:8000` | Connexity backend base URL |
| `CONNEXITY_API_TOKEN` | — | Bearer JWT for result submission |
| `MOCK_VOICE_AGENT_HTTP_PORT` | `8766` | Local HTTP port |

### Connexity API token

```bash
curl -s -X POST "$CONNEXITY_API_URL/api/v1/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=changethis" | jq -r .access_token
```

Set `CONNEXITY_API_TOKEN` to that value.

## Behavior

- **Persona:** customer-support assistant (short spoken replies).
- **Tools:** `lookup_order` mock (matches `examples/test-cases/normal-refund-request.json`).
- **Recording:** merged call audio via Pipecat `AudioBufferProcessor`.
- **Submission:** automatic on call disconnect via `connexity.submit_call_to_connexity`.

## Troubleshooting

- **503 on `/incoming`:** set `MOCK_VOICE_AGENT_PUBLIC_BASE_URL`.
- **Call connects but no result:** check `CONNEXITY_API_TOKEN` and that the voice job is in `waiting_for_result`.
- **DTMF decode fails:** ensure the submitted WAV includes the caller-side tones.
- **Twilio never reaches the agent:** confirm the phone number webhook points at `/incoming` on the same tunnel as `MOCK_VOICE_AGENT_PUBLIC_BASE_URL`.
