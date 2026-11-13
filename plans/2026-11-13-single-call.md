# Single call: recording, transcript, tool calls

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Single call: recording, transcript, tool
  calls" (10.08, Stage Observe).
- **Design:** `designs/screens/Connexity Call.dc.html`, Claude Design export of
  2026-11-13, after Dmytro applied `designs/13-single-call.md` ("id rather do it via
  design first as it should be updated"). The prompt brings the screen up to date: a speech
  timeline instead of the waveform, tool calls inline (item 25), and "Found by a rule or
  a model" on findings. Earlier prompts: `designs/09-calls.md` (single call part),
  `designs/12-adjustments.md` item 25. The new export wins.
- **MCP:** adds `get_call(workspace_id, call_id)`.

## Goal

A person clicks a call on the Calls page and opens it. They hear the recording and read
the transcript, turn by turn, following the audio. Every tool call sits inline at its
moment as one collapsed line, expanding to its arguments and result. With question 1,
what the checks found is shown at its moment too.

"Open a call to hear the recording and read the transcript, with tool calls inline: one
collapsed line each, expanding to arguments and result. No issues or findings yet."
(roadmap entry, written before checks ran; see question 1)

## What exists today

- **Traces are stored for every call:** utterances with speaker and time, tool calls with
  name, arguments, result, status and time, and markers. There is also the recording's
  address from Retell (`recording_url`).
- **`GET /calls/{id}/trace`** returns the whole trace, its executions, findings and check
  runs. It also includes the call's parties, so the caller's full number, and nothing
  masks secrets in tool arguments or results. Design item 25 assumes they are masked.
- **The Calls page** (#194) lists calls; rows open nothing yet.
- **Retell's recording address** can expire when the agent signs its URLs (the demo
  agent's settings have the switch for it), so a stored address may not play days later.

## Changes

### Backend

- **`GET /api/v1/calls/{id}/screen`:** what the single call shows, and no more.
  - **Header:** agent name, start time, duration, the caller's last four digits (never
    the number), result, and the agent version ("Version 88").
  - **Timeline:** one ordered list of entries, each with its moment in seconds:
    - an **utterance:** speaker (agent or caller) and text;
    - a **tool call:** name, status (ok, failed, timed out, no result), duration,
      arguments and result, and the n8n workflow line when one ran ("Workflow:
      quote-lookup v7 · 9 steps");
    - with question 1, **findings:** each with its title and key, category, severity,
      `found_by` and the issue it belongs to, attached to the entries it points at.
  - **Secrets masked:** any argument or result value whose key looks secret (`key`,
    `token`, `secret`, `password`, `authorization`, `api_key`) becomes "••••", at any
    depth.
  - **Never sent:** the full caller or agent number, the raw provider payload.
- **`GET /api/v1/calls/{id}/recording`:** redirects to the recording. It asks Retell for
  the call's current recording address each time, so a signed address that expired
  still plays. If Retell cannot be reached, it falls back to the stored address. Same
  workspace check as the call.
- **`get_call(workspace_id, call_id)`:** the same header, timeline and findings for the
  assistant. Callers' last four digits only; secrets masked.

### Frontend

- **Calls page rows open the call** (`/calls/{id}`). Rows become links.
- **The single call screen, as the design export shows it, with item 25:**
  - **The page bar:** agent, date and time, duration, "•••• 4821", the result label,
    "Version 88".
  - **The recording:** a player across the full width, with play and pause, the time, and
    a seek bar. On the seek bar:
    - **a speech timeline** where the design has a waveform (question 2);
    - a small tick for each tool call;
    - with question 1, a mark for each finding, critical ones prominent and warnings
      quiet.

    Clicking a tick or mark jumps the audio and the transcript.
  - **With question 1, the findings:** a short list under the player, worst first. Each
    has its sentence (title and key), its category, "found by a rule" or "by a model",
    and a jump to its moment. The issue link waits for the Issue page (10.09).
  - **The transcript:**
    - turn by turn, Agent and Caller, highlighting the turn playing;
    - tool calls inline as one muted line ("schedule_appointment · ok · 820 ms"; a failed
      one in the severity colour), expanding to arguments and result in monospace, with
      "Show all" for long values;
    - with question 1, findings inline at their turn or tool call;
    - when the call has a critical moment, it opens scrolled there.
- **Left out because they do not work yet** (rule 14):
  - the simulated-call line ("Proves: …"), until test runs exist;
  - the issue links, until the Issue page exists.

### Docs

- `docs-internal/mcp-architecture.md` lists `get_call`; the calls guide covers it.

## Decisions

Decided by Dmytro:

- Tool calls inline, one collapsed line each, expanding to arguments and result
  (2026-11-12, `frontend/CLAUDE.md`; design item 25).
- The deepest view is a single call; no drill-down below it (2026-11-12).
- The client consents to the demo; callers' details are blurred in the video
  (2026-11-13).

Proposed by Claude:

- A screen-shaped answer instead of the raw trace, so the caller's full number never
  reaches the browser, and secrets are masked.
- The recording is fetched fresh from Retell through the backend, because signed
  addresses expire.

## Answered questions

Dmytro (2026-11-13):

1. Findings are shown at their moment: marks on the recording, the findings list and
   inline in the transcript ("yes, show").
2. A speech timeline instead of a waveform, designed first in Claude Design
   (`designs/13-single-call.md`) before the build.

The new export arrived on 2026-11-13 ("Connexity design review (3)"); only the Call
screen and the project canvas changed.

## Done when

- `make check` and `pnpm build` pass. Backend tests cover:
  - the screen answer's header (last four digits, version, duration, result);
  - the timeline in order, with utterances and tool calls;
  - secrets masked at any depth;
  - findings attached to their entries (question 1);
  - the full number and raw payload never sent;
  - another workspace's call is not found;
  - the recording redirect to the fresh address, with the stored one as fallback;
  - `get_call`.
- Played through on a running backend: the screen answer and the recording redirect for
  invented calls, and `get_call` through MCP.
- **For Dmytro to check on screen** (app.connexity.ai after merge, in the demo workspace):
  - a Calls row opens the call;
  - the recording plays, and clicking a tick or mark jumps;
  - the transcript follows the audio;
  - a booking tool call expands to its arguments and result;
  - with question 1, a failed call opens at its critical moment, with the finding on the
    booking call;
  - dark and light.

## Out of scope

- Issue links (10.09) and simulated calls ("Proves: …").
- Editing, labelling or exporting a call; anything below the single call.
- n8n workflow steps on screen (one quiet line only, design item 25).

## Risks

- **Real caller details** are in the recordings and the booking tool's arguments. That
  is consented and blurred in the video. The screen shows no more than the design does.
- **Secret masking by key name** misses a secret stored under an innocent key. Retell's
  tool arguments rarely carry secrets; the masking covers the common names.
- **Retell recording access:** if Retell refuses the recording (deleted, or a storage
  setting), the player says "Recording unavailable".

## Outcome

### Deviations from the plan

- **The recording route answers the address; it does not redirect.** The web app reaches
  the backend through its own proxy, which follows redirects. A redirect would have
  streamed every recording through the web server and broken seeking. So
  `GET /calls/{id}/recording` answers `{url}` (fresh from Retell, or the stored one),
  and the player loads it straight from Retell.
- **A finding's moment is the last event it points at.** For "Two bookings for one slot"
  that is the second booking, where it went wrong; both bookings still show the
  finding (found in the play-through).
- **The finding reads "Title: key",** for example "Two bookings for one slot:
  schedule_appointment", as on the Calls page.
- **Issue links are left out** until the Issue page exists (10.09), as are the simulated
  call's "Proves" line and its labels.
- **Calls page rows now open the call.**

### Check results

`make check` on the final tree: see the table below. `pnpm build` also succeeds, with
`/calls/[id]` among the routes.

| Step | Result |
|---|---|
| Plan present and complete | ok |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

New tests (`test_call_screen.py`, 10):

- secrets masked at any depth;
- the screen answer: header (last four digits, duration, version, result, recording),
  the timeline in order, the tool call's status, duration, masked arguments and result,
  the finding with category, severity, `found_by` and its entry, and the full number,
  the secrets and the platform's payload never sent;
- a finding on two events sitting at the later one;
- another workspace's call not found, for both routes;
- the recording asked of Retell with the connection's key;
- the stored address as fallback on an error, an answer that is not JSON, or a timeout;
- no recording anywhere;
- `get_call` through MCP, and a call it cannot find.

MCP server: `get_call` is listed as read-only and reads the call.

**Played through on a running backend** (port 8026, local database). One invented call:
two identical bookings, with a secret in the booking's arguments, and Retell's call read
answered with a new signed address.

| # | Request | Came back |
|---|---|---|
| 1 | `GET /calls/{id}/screen` | "Front desk", "••••4821", 73 s, version 88, failed, recording available |
| 2 | Its timeline | Agent and caller turns, then `schedule_appointment · ok · 800 ms` and `· 900 ms`; `api_key` shown as "••••" |
| 3 | Its finding | "Two bookings for one slot: schedule_appointment", Booking, critical, rule, at the second booking (after the fix) |
| 4 | The full number or the secret anywhere in the answer | Neither |
| 5 | `GET /calls/{id}/recording` | The fresh signed address |
| 6 | Not signed in | 401 |

The backend log had no errors.

`/code-review` (high) raised five findings. Fixed:

- the finding's moment;
- an unreadable Retell answer breaking the recording route.

Not fixed:

- **The 1.x trace route still sends the full number** and unmasked tool values. Nothing
  on screen uses it now; deleting it would need your OK (REBUILD.md does not list it).
- **Masking by key name** over-masks keys like `author` and misses a secret under an
  innocent key.
- **Each call page asks Retell for the recording** once, which counts against Retell's
  limit. On a 429 it falls back to the stored address.

**For Dmytro to check on screen** (app.connexity.ai after merge, in the demo workspace):

1. A row on the Calls page opens the call; the back arrow returns to Calls.
2. The page bar: the agent, "Today 09:42 · 2 min 26 s · •••• 1234 · Version 88" and the
   result.
3. **The recording:**
   - it plays and pauses;
   - the Agent and Caller lanes show who spoke when, and the playhead moves;
   - clicking a lane, a tool tick or a finding mark jumps the audio and the transcript;
   - with no recording, "Recording unavailable".
4. **A failed booking call** opens scrolled to its critical moment. The finding sits in
   the list ("Booking · Found by a rule") and inline on the booking tool line.
5. A tool line, "schedule_appointment · ok · 820 ms", expands to Arguments and Result
   in monospace; "Show all" appears for long values; secret values show as "••••".
6. The transcript highlights the playing turn and follows the audio.
7. Dark and light both look like the design.

### Not done

- **Issue links** (10.09). **Simulated calls'** "Proves" line (test runs).
- **Deleting the 1.x trace route** (needs Dmytro's OK).
- **Throwaway data in the local dev database:** one more play-through user and call.
