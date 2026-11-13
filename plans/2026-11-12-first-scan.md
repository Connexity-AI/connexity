# First scan: every added agent's calls in the database

- **Owner:** Dmytro
- **Slice:** Milestone 1, feature 10 of the roadmap: "First scan: everything in the
  database".
- **Design:** No UI change. The Readiness screen already shows each step's state and
  detail line, which the backend writes. The progress bar and the "Open Home" button in
  `designs/12-adjustments.md` (item 19) come with the screens they need.
- **MCP:** adds `scan_calls(workspace_id)`. `get_readiness` and `add_agents` name it as
  the next step.

## Goal

After the person and the assistant add agents, the assistant brings in their past calls.
It does this once, through MCP, until it is finished. Every call is in the database as a
trace, with its versions resolved. Readiness steps 3 and 4 tick when it is done. From
then on the webhook (feature 8) keeps calls current.

Checks are not part of this feature (roadmap entry).

## What exists today

- **The on-request pull** (`sync_agent_calls`) asks Retell for an agent's calls after
  the newest stored one, 100 at a time, at most 2,000 per run. Each call is then read in
  full, mapped to a trace, has its versions resolved and is stored.
- **The webhook already stores new calls.** So "after the newest stored" skips the whole
  history as soon as one webhook call has arrived. The pull cannot be the first scan
  as it is.
- **Storing is idempotent** by Retell's call id, so a call the webhook already stored is
  not duplicated.
- **Readiness:**
  - step 3 is "in progress" with "N agents · M calls";
  - step 4 and `first_scan_done` are always "not started" and false.

## Changes

### Backend

- **Each added agent keeps the state of its first scan:**
  - when it started;
  - the window it covers;
  - how many calls Retell has in that window;
  - how far it has got;
  - when it finished.

  It is one migration on the agent table.
- **`POST /api/v1/mcp/workspaces/{workspace_id}/scan`**, one step of the scan per call:
  - **The first step for an agent** lists its calls in the window from Retell. Listing is
    cheap: no transcripts. This gives the total ("of 1,284") and fixes the window.
  - **Every step** reads calls in full, oldest first, from where the agent got to. It
    skips calls already stored (by the webhook or an earlier step), then maps, resolves
    versions and stores the rest through the same path as the webhook.
  - **Each step stops within a time budget,** about 40 seconds, below Cloud Run's request
    limit. Nothing runs in the background, because Cloud Run slows work after the answer
    is sent.
  - **Agents are scanned one after another,** oldest added first.
  - **The answer** gives each agent's "stored of total" and whether it is finished. Its
    next step is to call `scan_calls` again until everything is finished, then
    `get_readiness`.
  - **A step on a finished workspace** answers at once, with nothing to do.
  - **When every agent is finished,** one pass resolves versions for any call still
    unresolved. Calls whose versions Retell no longer has are counted and named in the
    answer, not retried forever.
- **Errors:**
  - Retell is unreachable: the step keeps what it stored and the next step is to try
    again.
  - Retell refuses the key: the next step is to reconnect through `connect_voice_platform`.
  - No agents added: the next step is `add_agents`.
- **An agent added after the first scan** has its own scan state, so `scan_calls` brings
  in its history too. The workspace's first scan stays done.
- **The 1.x on-request pull** (`sync_agent_calls`) is not changed in this pull request.

### Readiness

- **Step 3, "Agents and calls synced":**
  - **in progress:** "640 of 1,284 calls · 2 of 5 agents";
  - **done:** once every added agent's scan is finished, with "5 agents · 1,284 calls".
- **Step 4, "First scan done":**
  - **done** once step 3 is done for the first time;
  - its detail is "1,284 calls across 5 agents", plus "· 12 calls without versions" when
    any are unresolved;
  - `first_scan_done` becomes true and stays true.

  The design's "issues across agents" line waits for checks (proposed).
- **Next steps:**
  - `get_readiness` names `scan_calls` while any added agent is not finished;
  - `add_agents` adds it after the webhook step.

### MCP

- **The `scan_calls` tool** changes something, is not destructive and is safe to repeat.
  Its description says:
  - call it repeatedly until the answer says finished;
  - each call takes up to a minute.
- **The readiness guide** describes the first scan and what step 4 means.
- **`docs-internal/call-ingestion.md`'s "History" section** is updated from the
  incremental pull to the scan.

## Decisions

Decided by Dmytro (roadmap entry):

- The first scan brings every chosen agent's calls into the database as traces, with
  versions resolved, and Readiness steps 3 and 4 tick.
- Checks are not part of it.

Proposed by Claude:

- **The assistant drives the scan** in steps through MCP, each within a time budget. There
  is no background job, because of Cloud Run.
- **The scan keeps its own position per agent,** separate from the newest stored call,
  so webhook calls do not hide the history.
- **The first step lists the window** to know the total, for "640 of 1,284".
- **Calls are stored through the webhook's path.** That path still runs whatever checks
  are registered; this feature does not test or show them.
- **Step 4 ticks with step 3 and stays done.** Its detail is calls and agents, until
  checks exist.

## Answered questions

Dmytro accepted the recommendations ("accept", 2026-11-13):

1. The scan goes back 30 days.
2. Calls are read 5 at a time. The Retell service already does this
   (`_CALL_READ_CONCURRENCY`), so the scan reuses it.

## Done when

- `make check` passes. Backend tests (Retell mocked with `respx`) cover:
  - a full scan over several steps, with the time budget forced low, and its counts;
  - calls the webhook already stored, skipped and not duplicated;
  - the window;
  - Retell unreachable mid-scan (keeps what it stored, then resumes);
  - a revoked key;
  - no agents;
  - another workspace;
  - an agent added after the first scan;
  - unresolved versions counted;
  - Readiness steps 3 and 4, and `first_scan_done`;
  - the next steps in `get_readiness` and `add_agents`.
- Played through on running servers through MCP, with Retell mocked: steps until
  finished, Readiness ticking 3 and 4.
- **Dmytro, on app.connexity.ai after merge,** with agents added: ask the assistant to run
  the first scan. Step 3 counts up, and steps 3 and 4 tick when it says finished.

## Out of scope

- Running checks on the scanned calls, or showing issues (later features).
- The Calls page (feature 11) and call search (feature 12).
- A progress bar or "Open Home" on screen.
- Vapi and ElevenLabs.
- Removing the 1.x pull.

## Risks

- **Large accounts take many steps.** The 30-day window bounds it.
- **Retell's rate limits** during full reads, 5 at a time. A refused read stops the
  step before that call; the next step asks for it again.
- **Two scan steps at once for one workspace** (two assistants) could read the same
  calls twice. Storing is idempotent, and a row lock on the agent while it is scanned
  keeps the counts right.
- **Retell's list may change under the scan.** Calls deleted in Retell during the scan
  leave the total a little high; the scan skips them and finishes anyway.

## Outcome

### Deviations from the plan

- **The workspace records when its first scan first finished** (`Company.first_scan_done_at`,
  in the same migration as the agent's scan state). Step 4 stays done from it when agents
  are added later; the plan only said "stays done".
- **No row lock.** "Stored of total" is counted from the database and the position only
  moves forward, so two steps at once only repeat work; a lock would add nothing.
- **A step that lists a large window ends there;** reading starts the next step. The MCP
  server waits up to 180 seconds for a step (the plan said "up to a minute"), because a
  page that started before the 40 seconds ran out is finished (from `/code-review`).
- **Calls that started in the same millisecond** are all read: each page starts from the
  position's own millisecond, and calls already stored are skipped (from `/code-review`).
- **A call Retell will never return** (it answers 400, 404 or 422) is passed over instead
  of stopping the scan. That also applies to the 1.x pull, which shares the read
  (from `/code-review`).
- **Readiness's next step names `scan_calls` only when Retell agents are added,** so a
  1.x workspace with only Vapi or ElevenLabs agents is not sent in a loop (from
  `/code-review`).
- **The first step's answer** for an agent with a large window shows the total and 0
  stored; the next step stores the first page.

### Check results

`make check` on the final tree: see the table below.

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

New tests:

- `test_mcp_scan_calls.py` (13, Retell answers invented with `respx`):
  - a whole scan in steps, the first one only counting, with the counts, the answer's
    next steps and Readiness steps 3 and 4;
  - the window: a call from 40 days ago and a call still in progress are left out;
  - a finished workspace answers at once without asking Retell;
  - a call the webhook already stored is not read again;
  - Retell failing mid-scan keeps what was stored, then the scan carries on;
  - a revoked key, no agents, another workspace;
  - an agent added after the first scan (step 4 stays done, the new agent is scanned);
  - calls whose versions Retell no longer has are counted;
  - calls that started in the same millisecond across a page edge;
  - a call Retell refuses to return is passed over;
  - `add_agents` and `get_readiness` name `scan_calls`, and readiness does not for a
    workspace with no Retell agents.
- `test_retell_lists.py`: the call list without reads (window end, unfinished calls,
  malformed items), an empty window, and error, malformed, not-JSON and timeout answers;
  a call Retell will never return reads as nothing, a 503 is an error.
- MCP server: `scan_calls` is listed with its hints, posts to the scan route and waits
  180 seconds.

Migration `0014_agent_first_scan` applies, reverses and re-applies on the local database,
with no drift.

**Played through on a running backend** (port 8021, local database). Retell's answers
were invented inside the backend's process: one agent with 60 calls in the last 30 days
and one from 40 days ago. Pages were 10 calls, and the time budget was 0 so that each
step reads one page.

| # | Step | Came back |
|---|---|---|
| 1 | Readiness after adding the agent | Step 3 "in progress · 1 agent · 0 calls", step 4 not started |
| 2 | `scan` | 200: 0 of 60 stored (the window counted) |
| 3 | `scan` | 200: 10 of 60; Readiness "10 of 60 calls · 0 of 1 agent" |
| 4 | Two more steps, then one read made to fail | 200, 200, then 503 "Retell could not be reached during the scan" |
| 5 | Steps until finished | 38, 47, 56, 60 of 60, then finished, with "60 calls from 1 agent are in Connexity" |
| 6 | Readiness | Step 3 done "1 agent · 60 calls", step 4 done "60 calls across 1 agent", `first_scan_done` true |
| 7 | `scan` again | 200 at once, finished, 0 this step |

The backend log had no errors. A wrong token answered 401.

`/code-review` (high) raised eight findings. Fixed:

- a call Retell refuses to return stopped the scan;
- a step could outlast the MCP server's wait;
- 1.x Vapi or ElevenLabs agents sent the assistant in a loop;
- calls in the same millisecond at a page edge were skipped;
- the new Retell list had no timeout, empty or malformed tests;
- Readiness wrote to the database on a read.

Not fixed:

- **A call deleted in Connexity** is not read again by the scan and is not counted, so an
  agent can finish at "59 of 60". Deleting is a person's choice; the call stays deleted.
- **Step 3's total grows as the scan reaches each agent:** an agent's total is known only
  once its window is listed.

**For Dmytro, on app.connexity.ai after merge**, with Retell connected and agents added:

1. Ask the assistant to run the first scan. It calls `scan_calls` repeatedly.
2. Readiness step 3 counts up ("640 of 1,284 calls · 2 of 5 agents").
3. When the assistant says it is finished, steps 3 and 4 are done.

### Not done

- **Not tested against a real Retell account.**
- **A call Retell keeps failing to serve with a server error** stops that agent's scan
  until Retell serves it (noted in `REBUILD.md`).
- **The progress bar and "Open Home"** wait for their screens.
- **Throwaway data in the local dev database:** three play-through users, each with a
  test Retell connection, one agent and up to 60 invented calls.
