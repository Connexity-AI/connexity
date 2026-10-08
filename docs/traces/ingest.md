# Sending a trace to Connexity

Use this when your calls do not come from a provider Connexity has a built-in mapping
for: a self-hosted agent (Pipecat, LiveKit Agents, your own service), or a script that
converts another system's calls. You send each call as a [trace](./trace-schema.md).

## 1. Create an ingest token

An ingest token can send traces for your company's agents and do nothing else. It
cannot read anything.

```bash
curl -X POST "$CONNEXITY_URL/api/v1/ingest-tokens/" \
  -H "Content-Type: application/json" \
  --cookie "auth_cookie=$YOUR_SESSION" \
  -d '{"name": "production agent"}'
```

The response includes `token`. **It is shown only once**; Connexity stores a hash, not
the token. Keep it in your service's secrets.

- `GET /api/v1/ingest-tokens/` lists your tokens (name, visible prefix, created, last
  used, revoked). It never returns a token.
- `DELETE /api/v1/ingest-tokens/{id}` revokes one. It stops working immediately.
- A token does not expire on its own.

## 2. Send a trace

```bash
curl -X POST "$CONNEXITY_URL/api/v1/ingest/traces" \
  -H "Authorization: Bearer $CONNEXITY_INGEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "agent_id": "the agent's id in Connexity",
  "trace": {
    "schema_version": 1,
    "provider": "pipecat",
    "external_id": "session-7f3",
    "started_at": "2026-10-02T18:40:00Z",
    "events": [
      { "id": "1", "type": "utterance", "speaker": "caller", "text": "Hello?" },
      { "id": "2", "type": "utterance", "speaker": "agent", "text": "Hi, how can I help?" }
    ]
  },
  "raw": { "anything": "your system's own record of the call, kept unmodified" }
}
JSON
```

| Field | Required | |
|---|---|---|
| `agent_id` | yes | The Connexity agent the call belongs to. It must belong to the token's company. |
| `trace` | yes | The call, in the [trace format](./trace-schema.md). See the [examples](./examples/). |
| `raw` | no | Your system's original record of the call. Stored unmodified beside the trace. |

## 3. Read the response

```json
{
  "call_id": "6f1c…",
  "created": true,
  "capabilities": ["timing", "inputs"],
  "missing_capabilities": ["tool_calls", "tool_results", "components", "recording", "outputs"]
}
```

- `created` is `false` when the call already existed and its trace was replaced.
- `capabilities` and `missing_capabilities` tell you what Connexity can and cannot do
  with this trace. A check that needs a missing capability is skipped for the call. See
  [Capabilities](./trace-schema.md#capabilities).

## Sending a call again

A call is identified by its `external_id` within an agent. Sending the same
`external_id` again **replaces** the stored trace whole. That is how you re-send past
calls after fixing your mapping. It also means a wrong resend overwrites a good trace,
so include `raw` if you may need to rebuild it.

## Errors

| Status | Meaning |
|---|---|
| 401 | The token is missing, unknown or revoked. The response does not say which. |
| 404 | No agent with that id in the token's company. |
| 413 | The request body is larger than 5 MB. |
| 422 | The trace does not match the format; the response names the field. Also returned when a trace has more than 5,000 events. |

There is no rate limit yet. Please do not rely on that.
