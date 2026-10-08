# Retell calls

Connexity has a built-in mapping for Retell. Every Retell call it sees is converted to a
[trace](./trace-schema.md), and Retell's original payload is kept beside it, unmodified.

Calls arrive two ways.

## Pull

When an agent is linked to a Retell account and a Retell agent, Connexity pulls its
calls on request ("Refresh") and in the background when the Calls screen is opened and
the list is stale. Nothing to set up.

## Webhook

A webhook makes calls arrive as they end. Connexity does not configure Retell; you (or
your assistant) add the webhook in Retell:

```
POST {CONNEXITY_URL}/api/v1/webhooks/retell/{integration_id}
```

`integration_id` is the id of the Retell account connected in Connexity
(`GET /api/v1/integrations/`).

- **Use the API key with the "webhook" badge.** Retell signs each webhook with that key
  only. Connexity verifies the signature with the key the account was connected with,
  so if a different key was connected, every webhook is refused with 401 and calls
  arrive by pull only.
- A request is refused when the signature is missing or wrong, or its timestamp is more
  than five minutes from now.
- `call_ended` and `call_analyzed` are stored. `call_analyzed` arrives second for the
  same call and replaces the first trace, adding the analysis as outputs.
- Every other event, and a call for a Retell agent that is not linked to a Connexity
  agent, is answered with 200 and ignored, so Retell does not retry.

## What becomes what

| Trace | From Retell |
|---|---|
| `external_id`, `started_at`, `ended_at` | `call_id`, `start_timestamp`, `end_timestamp` |
| `channel`, `direction`, `parties` | `call_type`, `direction`, `from_number`, `to_number` |
| `end_reason`, `end_reason_detail` | `disconnection_reason`, grouped onto the fixed list; the original text is kept |
| `inputs` | `retell_llm_dynamic_variables` |
| `components` | the agent: `agent_id`, `agent_name`, `agent_version` |
| `events` | `transcript_with_tool_calls` |
| `outputs` | `call_analysis` and `collected_dynamic_variables` |
| `recording_url` | `recording_url` |
| `extensions` | latency, cost, token usage, `metadata`, the log link, call status |

Events:

- Speech by `agent`, `user` and `transfer_target` becomes utterances with speakers
  `agent`, `caller` and `other`. Times come from the word timings.
- A tool invocation and its result are joined into one tool call. With no logged result
  the status is `no_result`; with a result marked unsuccessful it is `error`.
- Node transitions, keypad presses and anything else in the timeline become markers.
- **Events are ordered by start time.** Retell lists overlapping speech in the order it
  finished recognising it, so its own order is not always the order things began. An
  item with no time stays right after the item it followed.
- Retell logs every tool call, so the trace sets `reports_tool_calls`: no tool call
  events means the agent made none.

A call that never connected has no start time; it is placed at the moment it ended and
has no events.
