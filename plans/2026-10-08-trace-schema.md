# Canonical call trace: schema, storage and validation

- **Owner:** Dmytro
- **Slice:** 1.1

## Goal

Give Connexity one shape for a call, whatever provider it came from. Today the `call`
table stores each provider's transcript in that provider's own format and the frontend
untangles three formats at display time, so nothing downstream has a single thing to
read. After this merges, a trace can be validated, stored and read back in one
provider-neutral shape. No real calls flow through it yet; slice 1.2 adds the endpoint
and slice 1.3 moves Retell onto it.

## Changes

**The wire format** (what a mapping sends and what the API will return)

- Public document `docs/traces/trace-schema.md` defines it: identity, optional context
  (source, channel, direction, end reason, parties, recording), inputs, components with
  versions, one ordered list of events, outputs, extensions.
- Three kinds of event: `utterance`, `tool_call` (arguments and result together) and
  `marker`. Every event may carry start and end times in milliseconds from call start.
- Validation models for it in the backend, including a version number
  (`schema_version: 1`).
- A function that derives a trace's **capabilities** (`tool_calls`, `tool_results`,
  `timing`, `inputs`, `components`, `recording`, `outputs`), as defined in the document.

**Storage** (each part of a trace is stored once; there is no stored JSON document)

- `call` table: the Retell-specific columns `retell_call_id` and `retell_agent_id` are
  renamed to `external_id` and `provider_agent_id`, and a `provider` column is added.
  New columns for the trace's call-level fields: source, channel, direction, ended at,
  end reason and its detail, both phone numbers, recording link, trace id, schema
  version, and free-form `inputs`, `outputs` and `extensions`.
- New `call_event` table: one row per event, ordered within the call, with typed
  columns for type, speaker, text, tool name, status, start, end, interrupted and span
  id, and JSON only for tool arguments, tool results and marker detail.
- New `call_component` table: one row per component (kind, name, ref, version,
  fingerprint).
- Functions to store a trace as rows and to assemble a trace from rows.
- One migration.

**What existing features notice**

- The API field `retell_call_id` on a call becomes `external_id`, and `retell_agent_id`
  becomes `provider_agent_id`. The frontend is updated; the generated client changes.
- Nothing else. The existing call sync for Retell, Vapi and ElevenLabs keeps writing the
  provider-format transcript into the existing `transcript` column, and the Calls screen
  keeps reading it. Both switch over in slice 1.3.

## Decisions

Made by Dmytro on 2026-10-08:

- The timeline is one ordered list of events with timings; a tool call carries its
  arguments and its result together.
- Real, test and simulated calls share this one format, told apart by `source`.
- Events are stored as rows, not as a JSON document, so there is one source of truth
  and aggregates use plain SQL.
- A trace stores the caller's phone number and the recording link.
- OpenTelemetry is not the trace format. Traces carry optional trace and span ids, the
  document maps traces to spans, and an OpenTelemetry endpoint is a later mapping.

Proposed by Claude and approved by Dmytro with this plan on 2026-10-08:

- `provider` is free text, not a fixed list, so a new stack needs no change here.
- Timing is optional. A trace without timestamps is valid; checks that need timing will
  be skipped for it and say so.
- Tool arguments, tool results and marker detail stay as JSON inside their event row,
  because their shape differs for every tool. They are stored once.
- The provider's original payload stays stored beside the call (the existing `raw`
  column). It is the source a mapping worked from, kept so a trace can be re-derived if
  a mapping is fixed. Nothing reads it as a trace.
- The old `transcript`, `status` and `duration_seconds` columns stay until slice 1.3
  removes them, so the Calls screen keeps working in between.
- The example traces in the repo use invented data only.

## Done when

- Three hand-built example traces validate: one shaped like a Retell call, one like a
  Vapi call, one like a self-hosted agent that supplies text only (no timing, no tools,
  no versions).
- Each example survives a round trip: stored as rows, read back, equal to the original.
- Capabilities derived for the three examples match what the document says they should
  be; the text-only example has none of the optional ones.
- Invalid traces are rejected with a clear error: an unknown event type, two events with
  the same id, a tool call with an unknown status, an event that ends before it starts.
- Deleting a call deletes its events and components.
- The existing call tests still pass with the renamed fields, and the Calls screen's
  code compiles against the regenerated client.
- `make check` passes, including the test that models and migrations agree.

## Out of scope

- An endpoint to send a trace to, and tokens for it (slice 1.2).
- Converting real provider payloads into traces (slice 1.3 for Retell; Vapi and
  ElevenLabs after it).
- Skill executions, CRM data and the detail of component versions (slices 1.4 to 1.6).
  This slice only creates the place they attach to.
- Any change to the Calls screen beyond the two renamed fields (slice 1.7).
- Moving eval transcripts to this format (Phase 4).
- An OpenTelemetry endpoint.

## Risks

- **The shape is untested against real calls.** It is designed from the providers'
  documented payloads and the existing mappers, not from live data. Slice 1.3 is where
  it meets real Retell calls, and it may need changes then. That is expected; the
  schema version exists for it.
- **Rows for every event grow fast.** A five-minute call is roughly 50 to 100 events.
  This was accepted in exchange for one source of truth and plain SQL aggregates.
- **Two transcript representations exist until slice 1.3:** the old provider-format
  column that the screen reads, and the new event rows that nothing writes yet. If 1.3
  slips, this in-between state lingers.
- **A reviewer should push back if** a field name reads as one provider's concept, or if
  something a second stack would obviously need is missing.

## Outcome

### Deviations from the plan

- **New field `reports_tool_calls`.** The plan derived every capability from what a
  trace contains. That does not work for tool calls: a trace with no `tool_call`
  events can mean "the agent called nothing" or "this provider does not expose tool
  calls", and a check for invented numbers must tell them apart. A mapping that
  includes every tool call now sets `reports_tool_calls: true`. Without it, a trace
  with no tool calls does not get the `tool_calls` capability. The schema document
  explains this.
- **Unknown fields are rejected.** Not stated in the plan. A typo in a mapping is an
  error instead of silently dropped data; anything without a field goes in
  `extensions`.
- **`provider` on a call is now read from the call itself.** The call list and detail
  responses used to look the provider up through the integration. They now return the
  call's own `provider` column, so a call without an integration shows its provider
  too. Existing calls are backfilled from their integration by the migration; calls
  with no integration get `unknown`.
- **The frontend needed no change.** The plan expected it to use the two renamed
  fields. It does not reference them; only the generated client changed.
- **Example file names** describe what they show (`hosted-platform-full`,
  `hosted-platform-partial`, `self-hosted-text-only`) instead of naming a provider,
  though two of them use `retell` and `vapi` as their `provider` value.

### Check results

`make check` on this branch:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 9s |
| Backend tests and coverage | ok | 83s |
| MCP server tests | ok | 3s |
| Frontend lint | ok | 12s |
| Frontend types | ok | 9s |
| Generated client is fresh | ok | 10s |

Note on the plan step: in the full run it failed, because this Outcome was not yet
written and because this branch was then stacked on the plan-rule branch (#163), so
the diff against `main` held two plan files. After #163 merged, the branch was rebased
onto `main` and the plan step was re-run on its own and passed. The other steps were
not re-run after the rebase; the code is unchanged by it.

Against the plan's done-when:

| Done when | Result |
|---|---|
| Three example traces validate | Yes: 45 new tests, all passing |
| Each survives a round trip through the database | Yes, including a start time given in a non-UTC zone |
| Capabilities match the document | Yes: all seven, four, and none |
| Invalid traces are rejected clearly | Yes: unknown event type, duplicate id, unknown status, end before start, plus end without start, call ending before it starts, unknown field, unknown speaker, provider with capitals or spaces, start time without a zone |
| Deleting a call deletes its events and components | Yes |
| Existing call tests pass with the renamed fields | Yes |
| Models and migrations agree | Yes |

Migration `0002_call_trace`, tested by hand on a scratch database holding two existing
calls: both kept their identifiers under the new column names; the one with an
integration got that integration's provider and the one without got `unknown`;
downgrade restored the old column names and data; re-upgrade succeeded; `alembic check`
reported no drift.

Review of the diff by the building session found one issue, not fixed here: two
simultaneous stores of the same new call would collide on the unique constraint and
one would fail with a database error. Nothing calls `store_trace` concurrently yet;
slice 1.2 adds the endpoint and must handle it. `/code-review` was not run as a
separate pass.

### Not done

- The existing features this touches (calls list and drawer, call sync, call labels,
  test cases linked to a call) were not smoke-tested by hand. Their automated tests
  pass.
- No real provider payload has been converted into a trace. The shape is still
  untested against live calls, as the plan's Risks say.
- The concurrent-store collision above.
- Skill executions, CRM data, check findings and comments do not exist yet, so nothing
  references an event row. The plan only promised the place for them.
