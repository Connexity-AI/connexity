# Call trace schema

> **Status: schema version 1.** Connexity can validate, store and read back a trace in
> this shape. There is no endpoint to send one to yet, and no provider is mapped to it
> yet; both are coming. Worked examples are in [`examples/`](./examples/).

A **trace** is Connexity's record of one call: who said what and when, what tools the
agent called and what came back, what the agent was given before the call, and which
version of each component served it.

Every provider records calls differently. Connexity defines this one shape and a
**mapping** converts a provider's payload into it. Checks, the call screen and the
assistant's tools read only this shape, so they work the same for Retell, Vapi,
ElevenLabs, or a self-hosted agent on Pipecat or LiveKit.

## Rules of the format

- Unknown fields are rejected. Anything a mapping wants to keep that has no field goes
  in `extensions`.
- `provider` is lower case with no spaces (`retell`, `pipecat`, `my-stack`).
- `started_at` and `ended_at` carry a time zone.
- Event `id`s are unique within a trace.
- An event with `end_ms` must have `start_ms`, and cannot end before it starts.
- An empty `components` list, or `parties` with no numbers, is the same as leaving the
  field out.

## Design rules

1. **Small required core.** A mapping that can only supply the conversation text is
   still valid. Everything else is optional.
2. **Missing is not the same as empty.** A field a mapping cannot supply is omitted, not
   filled with a guess. Connexity derives a list of **capabilities** from what is
   present, and each check declares the capabilities it needs.
3. **Nothing is thrown away.** The provider's original payload is stored next to the
   trace, unmodified.
4. **Time is first class.** On a voice call, *when* something happened decides whether
   it was a bug. An agent that states a price while its pricing tool is still running
   invented that price. The schema can express that.
5. **No provider words.** No field is named after a provider's concept.

## Shape

```jsonc
{
  "schema_version": 1,

  // ── Identity (required) ────────────────────────────────────────────
  "provider": "retell",              // free text, lower case; not an enum
  "external_id": "call_8f2c...",     // the provider's own id; unique per agent
  "started_at": "2026-09-30T14:02:11Z",

  // ── Context (optional) ─────────────────────────────────────────────
  "source": "production",            // production | test_call | simulation
  "channel": "phone",                // phone | web | text
  "direction": "outbound",           // inbound | outbound
  "ended_at": "2026-09-30T14:06:40Z",
  "end_reason": "caller_hangup",     // see "End reasons"
  "end_reason_detail": "user_hangup",// the provider's own wording, verbatim
  "trace_id": "4bf92f35...",         // optional; copied from the source when it has one
  "parties": {
    "agent_number": "+15550100",
    "caller_number": "+15550123"
  },
  "recording_url": "https://...",

  // ── What the agent was given (optional) ────────────────────────────
  "inputs": {                        // variables set before the call started
    "customer_name": "Dana",
    "plan": "standard"
  },

  // ── What served the call (optional) ────────────────────────────────
  "components": [
    { "kind": "agent",  "name": "Booking agent",  "ref": "agent_71a...", "version": "14" },
    { "kind": "flow",   "name": "Booking flow",   "ref": "flow_c02...",  "version": "9" },
    { "kind": "model",  "name": "gpt-4.1" },
    { "kind": "skill",  "name": "get_quote",      "ref": "wf_Kq1...",    "version": "37" }
  ],

  // true when the mapping includes every tool call the agent made (see "Capabilities")
  "reports_tool_calls": true,

  // ── The conversation (required, may be empty for a call that never connected) ──
  "events": [
    { "id": "e1", "type": "utterance", "speaker": "agent",
      "text": "Hi Dana, I'm calling about the repair visit you asked for.",
      "start_ms": 900, "end_ms": 4200 },

    { "id": "e2", "type": "utterance", "speaker": "caller",
      "text": "Sure. How much will it cost?",
      "start_ms": 4800, "end_ms": 6900 },

    { "id": "e3", "type": "tool_call", "name": "get_quote",
      "arguments": { "service": "boiler_repair", "plan": "standard" },
      "status": "ok",                // ok | error | timeout | no_result
      "result": { "price": 180 },
      "start_ms": 7000, "end_ms": 9400 },

    { "id": "e4", "type": "utterance", "speaker": "agent",
      "text": "The visit is one hundred and eighty dollars.",
      "start_ms": 9600, "end_ms": 12800 },

    { "id": "e5", "type": "marker", "name": "transfer",
      "detail": { "to": "human_scheduler" }, "start_ms": 31000 }
  ],

  // ── What the provider concluded afterwards (optional) ──────────────
  "outputs": {                       // post-call extraction or analysis, verbatim
    "outcome": "booked",
    "quoted_price": "180"
  },

  // ── Anything the mapping wants to keep that has no field (optional) ─
  "extensions": { "latency_p50_ms": 820, "cost_usd": 0.41 }
}
```

## Events

`events` is one ordered list. Order is the order things happened. There are three kinds.

### `utterance`

Something a party said.

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique within the trace. Checks and comments point at it. |
| `speaker` | yes | `agent` or `caller`. |
| `text` | yes | What was said, as transcribed. |
| `start_ms`, `end_ms` | no | Milliseconds from the start of the call. |
| `interrupted` | no | `true` if the other party cut it off. |

### `tool_call`

One call from the agent to a tool, **with its outcome in the same event**. Providers
usually log the request and the result as two entries; the mapping joins them.

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique within the trace. Skill executions attach to it. |
| `span_id` | no | Copied from the source when it has one. |
| `name` | yes | The tool's name as the agent knows it. |
| `arguments` | no | Parsed JSON object. |
| `status` | no | `ok`, `error`, `timeout`, or `no_result` (the call ended first, or the provider logged no result). |
| `result` | no | Parsed JSON if it parses, otherwise the raw string. |
| `start_ms`, `end_ms` | no | When the call was issued and when the result arrived. |

### `marker`

Something that happened that is neither speech nor a tool call: a transfer, a hold, a
voicemail detection, a keypad press, a move between nodes of a flow.

| Field | Required | Notes |
|---|---|---|
| `id`, `name` | yes | `name` is free text chosen by the mapping. |
| `detail` | no | Any JSON object. |
| `start_ms` | no | |

## Components

`components` lists what served the call. Each entry has a `kind` (`agent`, `flow`,
`prompt`, `model`, `voice`, `skill`, or any other word), a `name`, and optionally the
provider's `ref`, a `version`, and a `fingerprint` (a hash of the content, for
components that have no version number).

Connexity uses this to answer "which version was this call on?" and later to tell
verified versions from unverified ones. A mapping supplies whatever the provider
reports with the call.

## End reasons

`end_reason` is one of a short fixed list so calls can be compared across providers.
The provider's exact wording always goes in `end_reason_detail`.

| Value | Meaning |
|---|---|
| `caller_hangup` | The caller ended the call. |
| `agent_hangup` | The agent ended the call. |
| `transfer` | The call was handed to another party. |
| `voicemail` | The call reached voicemail or a screener. |
| `no_answer` | Nobody picked up, or the line was busy. |
| `error` | A technical failure ended the call. |
| `limit` | A time or silence limit ended the call. |
| `unknown` | The mapping cannot tell. |

## Capabilities

Connexity derives these from a trace and reports them when it is ingested. A check that
needs a capability the trace lacks is skipped for that trace and says so; it does not
pass silently.

| Capability | Present when |
|---|---|
| `tool_calls` | At least one `tool_call` event exists, or `reports_tool_calls` is `true`. |
| `tool_results` | `tool_calls` is present and every `tool_call` has a `status`. |
| `timing` | There is at least one event and every event has `start_ms`. |
| `inputs` | `inputs` is present. |
| `components` | `components` has at least one entry with a `version` or `fingerprint`. |
| `recording` | `recording_url` is present. |
| `outputs` | `outputs` is present. |

**Why `reports_tool_calls` exists.** A trace with no `tool_call` events can mean two
different things: the agent called no tools, or the provider does not expose tool calls.
A check for invented numbers must tell these apart, because "the agent quoted a price
and called nothing" is exactly the failure it looks for. A mapping that does include
every tool call sets `reports_tool_calls` to `true`; then an empty list is evidence.

Example: the check "every dollar figure the agent says came from a tool result, an
input, or the caller" needs `tool_results` and `inputs`. With `timing` it can also catch
a figure spoken before the tool returned.

## How the three built-in providers fill it

| Field | Retell | Vapi | ElevenLabs |
|---|---|---|---|
| `external_id` | `call_id` | `id` | `conversation_id` |
| `events` | `transcript_with_tool_calls` | `messages` | `transcript` with `tool_calls` and `tool_results` |
| `inputs` | `retell_llm_dynamic_variables` | `assistantOverrides.variableValues` | `conversation_initiation_client_data.dynamic_variables` |
| `components` | `agent_id` + `agent_version` | `assistantId` | `agent_id` |
| `end_reason_detail` | `disconnection_reason` | `endedReason` | `metadata.termination_reason` |
| `outputs` | `call_analysis` | `analysis` | `analysis` |
| `recording_url` | `recording_url` | `artifact.recordingUrl` | not in the payload |

These columns are from the providers' documented payloads and have not yet been checked
against real calls. Slice 1.3 does that for Retell.

## Personal data

Phone numbers and recordings are personal data. A trace stores them when the provider
supplies them: `parties` is what lets Connexity match a call to its CRM record, and
`recording_url` is what the call screen plays. Both are also present in the stored
provider payload.

## Storage (internal)

The JSON above is the **wire format**: what a mapping sends and what the API returns.
It is not stored as a document. Each part of a trace is stored once:

- the call's own fields are columns on the call row;
- every event is a row in the `call_event` table, ordered by its position in the call, with
  typed columns for what is filtered and aggregated (type, speaker, tool name, status,
  start, end) and JSON only for free-form payloads (tool arguments, tool results,
  marker detail);
- every component is a row in the `call_component` table, so calls can be grouped by
  version;
- `inputs`, `outputs` and `extensions` are free-form key-value data on the call row.

A trace is assembled from these rows when it is read. Things that attach to a trace
later (skill executions, check findings, comments) reference an event row directly.

The provider's original payload is stored unmodified beside the call. It is the source
material a mapping worked from, kept so a trace can be re-derived if a mapping is
fixed; nothing reads it as a trace.

## OpenTelemetry

Connexity does not use OpenTelemetry as its trace format, but a trace converts to and
from OpenTelemetry spans:

| Trace | OpenTelemetry |
|---|---|
| The call | The root span |
| A `tool_call` event | A child span, from `start_ms` to `end_ms` |
| An `utterance` event | A child span, or a span event when it has no end time |
| `started_at` plus an event's `start_ms` | The span's absolute start time |

A trace may carry an optional `trace_id`, and each event an optional `span_id`, copied
from the source when it has them. They let a tool call be matched to the backend work
it triggered. Receiving OpenTelemetry spans directly from self-hosted agents (Pipecat,
LiveKit Agents) is planned as one more mapping.

## Versioning

`schema_version` is an integer. Adding an optional field does not change it. A change
that would make an older trace invalid increments it, and Connexity keeps reading older
versions.
