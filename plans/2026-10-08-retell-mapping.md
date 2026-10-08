# Retell calls arrive as traces

- **Owner:** Dmytro
- **Slice:** 1.3

## Goal

Make the trace real. Slices 1.1 and 1.2 built the shape and a way in, but no actual
call uses them: Retell calls are still stored in Retell's own format and the Calls
screen still untangles provider formats in the browser. After this merges, every
Retell call Connexity sees is converted to a trace, by pull and by webhook, and the
Calls screen shows calls from their traces.

## Changes

**The Retell mapping** (one module; the only place that knows Retell's call format)

- Converts a Retell call into a trace:

  | Trace | From Retell |
  |---|---|
  | identity, start, end | `call_id`, `start_timestamp`, `end_timestamp` |
  | channel, direction, parties | `call_type`, `direction`, `from_number`, `to_number` |
  | end reason and its detail | `disconnection_reason`, mapped to the fixed list; the original kept verbatim |
  | inputs | `retell_llm_dynamic_variables` |
  | components | the agent: `agent_id`, `agent_name`, `agent_version` |
  | events | `transcript_with_tool_calls`: speech becomes utterances with times from the word timings; a tool invocation and its result are joined into one tool call; node transitions, keypad presses and injected messages become markers |
  | outputs | `call_analysis` and `collected_dynamic_variables` |
  | recording | `recording_url` |
  | extensions | latency, cost, token usage, `metadata`, the debug log link |

- A tool call with no logged result gets status `no_result`. A result marked
  unsuccessful gets `error`.
- Retell reports every tool call, so the trace sets `reports_tool_calls`.

**Pull**

- The existing "refresh" and background sync for Retell now convert each call and store
  it as a trace, with Retell's original payload kept beside it.

**Webhook**

- New address for Retell to post to: `POST /api/v1/webhooks/retell/{integration id}`.
- Each request is verified with Retell's signature scheme (HMAC of the body and a
  timestamp, using the connected account's API key, rejected if older than five
  minutes).
- `call_ended` and `call_analyzed` are converted and stored; the second replaces the
  first and adds the analysis. Other events are acknowledged and ignored. A call for an
  agent Connexity does not know is acknowledged and ignored, so Retell does not retry.
- Connexity does not set the webhook up in Retell. The user or their assistant does.

**The call table and API**

- The old columns `transcript`, `status` and `duration_seconds` are removed.
- A call in the API gains `ended_at`, `end_reason`, `source` and whether it has a trace,
  and loses `transcript` and `status`.
- New: `GET /api/v1/calls/{id}/trace` returns the trace and its capabilities.

**The Calls screen**

- The list and the call drawer read the trace: utterances, tool calls with arguments,
  result and status, and markers, in order, with times when present.
- The browser code that untangled three provider formats is deleted.
- A call with no trace shows that it has not been converted yet.

**The trace format**

- One addition: a third speaker value, `other`, for a party that is neither the agent
  nor the caller. Retell reports the person a call was transferred to as a separate
  speaker, and the format had only two.

## Decisions

Proposed by Claude and approved by Dmytro on 2026-10-08:

- **Vapi and ElevenLabs calls lose their conversation display until they are mapped.**
  Their sync keeps creating calls with the original payload stored, but the screen will
  say "not converted yet" for them. Mapping them is a follow-up slice (1.3b).
- **Add the speaker value `other`** to the trace format (schema version stays 1; it is
  an addition).
- **No new scheduler.** Pull stays as it is today: on request, and in the background
  when an agent's calls are stale. The webhook is what makes calls arrive promptly.
- **The webhook is verified with the account's API key.** Retell only signs with the key
  that carries the "webhook" badge in its dashboard, so the Retell account must be
  connected to Connexity with that key, or webhooks will be refused.
- **Checking against real calls happens on Dmytro's machine only.** With a Retell
  account connected to the local app, the session pulls real calls into the local
  database, compares each trace with Retell's payload, and reports counts and field
  names. No real call content goes into the repo, the plan, or the pull request.
- **Test fixtures are invented** Retell payloads built from Retell's documented format.
- **Call sync no longer needs an environment.** It works from the agent's own link to
  its provider account and provider agent. Environments then have no remaining purpose;
  deleting them is left to a later slice.

## Done when

- Invented Retell payloads covering these cases convert to the expected traces: a plain
  conversation; a tool call with a successful result; a failed result; a tool call with
  no result; a transfer with a third speaker; a keypad press and a node transition; a
  web call; a call that never connected (no transcript).
- Each Retell disconnection reason maps to one of the fixed end reasons, and a reason
  Retell adds later maps to `unknown` with its text kept.
- Refreshing a Retell agent stores traces and the original payloads; refreshing again
  creates no duplicates.
- A correctly signed `call_ended` webhook stores a trace, and `call_analyzed` for the
  same call replaces it and adds the outputs.
- A webhook with a wrong signature, a missing signature, or a timestamp older than five
  minutes is refused, and nothing is stored.
- A webhook for an unknown agent, and an event type that is not handled, return success
  and store nothing.
- `GET /calls/{id}/trace` returns the stored trace; another company's call is not found.
- The Calls screen code compiles and renders from the trace; the old format-untangling
  code is gone.
- **On real calls** (needs Dmytro's Retell account connected locally): the last 30 days
  of reference agent 1's calls convert without error, and for every call the
  utterances in the trace equal, in order, the speech in Retell's payload. Reported as
  counts.
- `make check` passes.

## Out of scope

- Mapping Vapi and ElevenLabs (slice 1.3b).
- Matching a tool call to its n8n run (slice 1.4).
- Versions of the flow, prompt and skills. Only the agent's own version is filled here
  (slice 1.5).
- CRM data (slice 1.6).
- The full call screen: audio player, executions, CRM, versions panel (slice 1.7).
- Setting up the webhook inside Retell.
- A scheduler.

## Risks

- **Retell documents no timing for tool calls.** Speech has word-level times; tool
  invocations and results have none in the documented format. If real payloads have
  none either, Retell traces will lack the `timing` capability, and the check "a price
  was spoken while the tool was still running" cannot be exact for Retell; only the
  order of events will be known. Real calls will show whether there is more than the
  documentation says.
- **The mapping is built from documentation until real calls are checked.** The real
  check is in the done-when, and it depends on Retell access that is not set up yet.
- **Webhooks fail silently if the connected key is not the badged one.** Retell will
  retry three times and give up; calls would then only arrive by pull.
- **Removing the old columns is one-way.** Existing Vapi and ElevenLabs calls keep their
  original payload, so nothing is lost, but they show no conversation until 1.3b.
- **A reviewer should push back if** losing the Vapi and ElevenLabs display for a while
  is not acceptable, or if `other` is the wrong way to represent a third speaker.

## Findings from real calls, before building

Looked at the shape (field names, types, counts; no content) of 216 real Retell calls
synced into Dmytro's local database on 2026-10-08. Not yet acted on.

- **The connected agent makes no backend tool calls.** All 58 tool invocations in 216
  calls are Retell's built-in `end_call`. There are zero custom tool calls and zero
  tool results. All phone calls are inbound. Dmytro confirmed on 2026-10-08 that this
  is an inbound bot for the same client, not the offer bot. So the mapping of tool
  results and statuses cannot be checked on these calls; it rests on invented payloads
  built from Retell's documentation.
- **Tool invocations do carry a time** (`time_sec`), which Retell's documentation does
  not show. Node transitions and keypad presses carry it too. So the timing risk in
  this plan is smaller than written: 211 of 216 calls have a start time on every item.
- **Five calls contain an utterance with no word timings**, so those traces will lack
  the `timing` capability.
- **Retell's timeline is not strictly in time order.** In 100 of 216 calls, adjacent
  items are out of order by start time, almost always a caller and agent utterance
  overlapping (median 0.11 s, maximum 1.8 s). Dmytro decided on 2026-10-08: events are
  ordered by start time.
- There is an undocumented top-level `tool_calls` list with `start_time_sec` per call.
  It adds nothing the timeline lacks for these calls.
- Agent versions 1 to 50 appear across the calls, so the agent component's version will
  be well populated.

## Outcome

### Deviations from the plan

- **The real-call check is not the one the plan described.** The plan said "the
  utterances in the trace equal, in order, the speech in Retell's payload", on reference
  agent 1. Two things changed:
  - Events are ordered by start time (Dmytro, 2026-10-08), so the trace's order differs
    from Retell's listing wherever speech overlaps. The check became: the same
    utterances, compared as a set with counts, and every trace in start-time order.
  - The agent connected locally is an inbound bot, not the offer bot. Its calls contain
    no backend tool calls and no tool results. The mapping of tool results and their
    statuses is therefore tested on invented payloads only.
- **The 216 local calls were converted by a throwaway local script**, not by the
  product. The product only converts a call when its provider sends it (pull or
  webhook). Calls stored before this slice keep their original payload and show "not
  converted yet" until they are re-pulled. There is no product path that re-converts
  stored payloads.
- **The Calls page no longer asks for an environment**, and the fix made earlier in
  this session for the error on that page was reverted, because the code that caused it
  is gone.
- **The Calls list gained an "Ended" column** (the end reason). Not in the plan.
- **Call sync moved into its own module** (`services/call_sync.py`), and the log line
  that wrote every listed call to the server log was removed.
- **A public page was added**, `docs/traces/retell.md`: how calls arrive, how to set up
  the webhook, what maps to what.
- **A result with no logged invocation is kept** as a tool call named `unknown_tool`.
  The plan did not cover that case.

### Check results

`make check` on this branch:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 6s |
| Backend tests and coverage | ok | 55s |
| MCP server tests | ok | 2s |
| Frontend lint | ok | 2s |
| Frontend types | ok | 1s |
| Generated client is fresh | ok | 8s |

The plan step failed in the full run because this Outcome was not yet written. It was
re-run on its own afterwards and passed; nothing else changed in between.

Against the done-when (95 tests across the mapping, the webhook and the call routes):

| Done when | Result |
|---|---|
| Invented payloads convert: plain conversation, tool call with result, failed result, no result, transfer with a third speaker, keypad press and node transition, web call, call that never connected | Yes, one test each |
| Each Retell disconnection reason maps to a fixed reason; a new one maps to `unknown` with its text kept | Yes: all 39 known reasons, and an invented one |
| Refresh stores traces and original payloads; refreshing again creates no duplicates | Yes |
| Signed `call_ended` stores a trace; `call_analyzed` replaces it and adds outputs | Yes |
| Wrong, missing or stale signature is refused and nothing is stored | Yes: also a signature made with another key, one dated in the future, an unknown account and an account of another provider. All give the same 401 |
| Unknown agent and unhandled event return success and store nothing | Yes |
| `GET /calls/{id}/trace` returns the trace; another company's call is not found | Yes |
| The Calls screen compiles from the trace; the format-untangling code is gone | Compiles and lints. **Not looked at in a browser** |
| Real calls convert, with the same utterances | See below |
| `make check` passes | Yes, with the note above |

Real calls, on Dmytro's machine, counts only (216 calls of the connected inbound bot):

| Measure | Result |
|---|---|
| Converted without error | 216 of 216 |
| Stored trace reads back identical to the mapped trace | 216 of 216 |
| Same utterances as Retell's payload, compared as a set with counts | 216 of 216 |
| Same utterances in Retell's listing order | 116 of 216 (expected: 100 calls have overlapping speech, which sorting reorders) |
| Events in start-time order | 216 of 216 |
| Traces with timing on every event | 211 of 216 |
| Traces with inputs | 205 of 216 |

Migration `0004_call_drop_provider_columns` applies, reverses and re-applies on the
local test database, and `alembic check` reports no drift.

`/code-review` was not run as a separate pass.

### Not done

- **Not seen in a browser.** The drawer was rewritten and only type-checked.
- **The webhook was not tried against Retell.** The signature check is built from
  Retell's documentation and tested with signatures the tests compute the same way. If
  Retell signs differently in practice, every webhook is refused and calls arrive by
  pull only.
- **Tool results on real calls**: unchecked, as above.
- **Webhooks arriving out of order.** If `call_ended` arrives after `call_analyzed`, it
  replaces the fuller trace and the outputs are lost until the next pull of that call.
  Not handled.
- **A call whose integration was removed stays hidden** when it is sent again. Carried
  from slice 1.2, still not handled.
- **The 30-day window** in the done-when was not applied; all 216 local calls were used.
- Vapi and ElevenLabs calls show "not converted yet" (slice 1.3b), as decided.
- The local development database was not migrated to `0004`; run `make db-upgrade`.
