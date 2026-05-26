# Voice agent contract

For text-mode evals, see the [text agent contract](./text-agent-contract.md). Overview of both modes: [agent contracts](./agent-contract.md).

Voice-mode evals run over a **phone call**. Connexity acts as the simulated caller (via Twilio + Pipecat). Your agent answers the call, handles the conversation, and **after hangup** submits the call artifacts to Connexity.

The submitted result is **authoritative for judging**. Connexity does not judge from the simulated caller's transcript.

Canonical backend model: `VoiceSimulationResultSubmit` in `app.models.voice_simulation_job`.

Reference implementation: [examples/mock-voice-agent/](../examples/mock-voice-agent/) — all Connexity-specific integration helpers live in [`connexity.py`](../examples/mock-voice-agent/connexity.py).

## Call flow

1. User creates a voice eval config with your agent's **phone number** (`agent_phone_number`).
2. Connexity voice worker places an outbound Twilio call to that number.
3. Your agent answers (via your telephony stack — Twilio webhook, SIP, etc.).
4. During the call, Connexity sends **in-band DTMF tones** to identify the test case.
5. Your agent converses normally (STT → LLM → TTS or equivalent).
6. When the call ends, **your agent** POSTs the result payload to Connexity (see below).
7. Connexity downloads `audio_url`, decodes DTMF from the recording, attaches the result to the correct voice job, maps `messages` to a transcript, and runs the existing judge.

## Result submission endpoint

| | |
|---|---|
| **Method / path** | `POST /api/v1/voice-simulations/results` |
| **Content-Type** | `application/json` |
| **Auth** | `Authorization: Bearer <jwt>` (same login token as the Connexity UI / CLI) |

Do **not** send `test_case_id`, `run_id`, or DTMF code in the body. Connexity routes the submission by decoding DTMF tones from `audio_url`.

### Request body (`VoiceSimulationResultSubmit`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `audio_url` | string | yes | Public URL of a call recording that **includes Connexity's in-band DTMF tones**. Max 2048 chars. Must be reachable by the Connexity backend (`http`/`https`, no private IPs). |
| `messages` | array | yes | OpenAI-format conversation messages from **your agent's perspective** (see below). Min length 1. |

### `messages[]` (`ChatMessage`)

Same OpenAI chat shape as the [text agent contract](./text-agent-contract.md). Typical voice submissions include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | yes | `user`, `assistant`, or `tool` (omit `system` / developer prompts). |
| `content` | string \| null | no | Spoken/text content for the turn. |
| `tool_calls` | array | no | On `assistant`, OpenAI-style tool calls your agent invoked. |
| `tool_call_id` | string \| null | no | On `tool`, id of the call this message answers. |
| `name` | string \| null | no | On `tool`, function name. |

If you use Pipecat's `LLMContext`, `context.get_messages()` already returns OpenAI-compatible dicts — filter out `system` roles before submission.

### Response

Returns the matched `VoiceSimulationJobPublic` row (status moves to `completed` on success). Duplicate identical payloads are accepted idempotently.

## Example payload

```json
{
  "audio_url": "https://your-agent.example/recordings/CA1234567890abcdef.wav",
  "messages": [
    {
      "role": "user",
      "content": "Hi, I'm calling about order ORD-12345."
    },
    {
      "role": "assistant",
      "content": "Let me look that up for you.",
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "lookup_order",
            "arguments": "{\"order_id\": \"ORD-12345\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "name": "lookup_order",
      "content": "{\"order_id\": \"ORD-12345\", \"status\": \"delivered\", \"eligible_refund\": true}"
    },
    {
      "role": "assistant",
      "content": "Your order was delivered and is eligible for a refund. How can I help?"
    }
  ]
}
```

## Integration checklist

When adapting the mock voice agent for production, implement these Connexity touchpoints (see `examples/mock-voice-agent/connexity.py`):

1. **`audio_url`** — expose a public recording URL per call. The WAV/MP3 must preserve Connexity's DTMF tones from the caller leg. Twilio recording settings or merged pipeline audio both work if tones are audible.
2. **`messages`** — export your agent-side transcript in OpenAI format after hangup. Include tool calls and tool results if your agent uses tools.
3. **Result POST** — call `POST /api/v1/voice-simulations/results` with bearer auth when the call ends and both artifacts are ready.
4. **Phone number** — register the inbound number Connexity dials in your voice eval config (`agent_phone_number`).

Everything else (Pipecat pipeline, Twilio webhooks, STT/TTS providers, tool registry) is your agent implementation.

## Telephony (not prescribed)

This contract does not require Twilio, Pipecat, or a specific stack. You need:

- A phone number Connexity can dial.
- A voice stack that answers and converses.
- A recording that includes in-band DTMF.
- An HTTP client that submits the result after hangup.

The reference example uses Twilio Media Streams + Pipecat because that matches Connexity's local voice worker setup.

## What this is not

- Not a per-turn HTTP callback like text mode — one submission **after** the call.
- Not caller-side transcript submission — only your agent's `messages` are judged.
- Not explicit test-case routing in the JSON body — DTMF in `audio_url` is the routing key.
- Not platform-executed tools — your agent runs tools and includes results in `messages`.

## Examples in this repo

| Path | Purpose |
|------|---------|
| [examples/mock-voice-agent/](../examples/mock-voice-agent/) | Pipecat/Twilio inbound agent with annotated Connexity integration in `connexity.py`. |
| [examples/mock-text-agent/](../examples/mock-text-agent/) | Text-mode counterpart (`POST /agent/respond`). |
