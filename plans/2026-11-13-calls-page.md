# Calls page

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Calls page (no issues yet)" (10.07, Stage
  Observe).
- **Design:** `designs/screens/Connexity Calls.dc.html` (Claude Design export
  2026-11-12) for how the page looks. Prompt `designs/09-calls.md`, Calls page part. The
  screen wins where they differ.
- **MCP:** adds `list_calls(workspace_id, …)` with the same search and filters.

## Goal

A person opens **Calls** in the sidebar and sees the workspace's calls, newest first.
Each row shows the time, the agent, the caller as the last four digits, the duration
and, if accepted (question 1), the result and worst finding. They can find a call by
phone number or call ID and narrow the list with filters that work. The assistant can do
the same through MCP.

"The Calls page: newest first, caller as last four digits, duration, agent; search and
filters that work. No results, findings or issues yet." (roadmap entry, written before
checks ran; see question 1)

## What exists today

- **No Calls page.** The sidebar has no pages yet (`NAV_ITEMS` is empty); Readiness is
  the landing page. Pages are added by the feature that builds them.
- **The web API** lists one agent's calls (`GET /agents/{id}/calls`, 1.x, paged by
  offset). Nothing lists a workspace's calls, searches them or filters them.
- **Every call is checked** on arrival and in the minute pull (#192). Each has a result
  (failed, degraded, clean or unchecked), and its findings carry a category.
- **Calls store the caller's number** (`caller_number`) and Retell's call id
  (`external_id`); all calls are real (`source` = production).
- **The screen pattern:** server components read the generated SDK, as Readiness does.

## Changes

### Backend

- **`GET /api/v1/calls`** (the signed-in person's open workspace):
  - **Rows,** newest first, paged by an opaque cursor (25 a page, "Show more"):
    - time;
    - agent (id, name);
    - caller as the last four digits only, never the full number;
    - duration;
    - with question 1: the result and the worst finding in one plain line (the check's
      title and its key, for example "Booking with missing or placeholder details:
      schedule_appointment"), plus its category.
  - **Tiles for the period:** Calls, and with question 1, Failed, Degraded and Clean.
  - **Filters:**
    - agent;
    - period: last 7, 30 or 90 days (default 30);
    - with question 1, result (Failed, Degraded, Clean) and category (the fixed
      categories).
  - **Search** (question 2): one field.
    - **Digits** match the end of the caller's number, so "4821" or a full number with
      or without "+1" finds it.
    - **Anything else** matches a call id exactly: Connexity's own or Retell's.
- **`list_calls(workspace_id, query?, agent_id?, result?, category?, period?, cursor?,
  limit?)`** answers the same rows and tiles for the assistant. Callers are shown as the
  last four digits there too.

### Frontend

- **Calls in the sidebar,** in its decided place (after Agents, which is not built yet,
  so for now the only item). Readiness stays the landing page.
- **The Calls screen, as the design export shows it:**
  - the page bar with "Calls" and the period picker;
  - the number tiles;
  - one search field and compact filters, with "Clear";
  - the list: Time, Agent, Caller (•••• 4821), Duration, Result and Worst finding (with
    question 1);
  - "No calls match" with "Clear the search and filters";
  - "Show more".
- **Colour only for Failed and Degraded;** Clean stays quiet, and "Unchecked" shows as
  a quiet label.
- **Rows do not open anything yet.** The single call is 10.08, and a row that opened
  nothing would break rule 14.
- **Left out because they do not work yet** (rule 14):
  - the Source filter and the "Simulated" and "Test" labels: every call is real until
    test runs exist (question 3);
  - opening a row.

### Docs

- `docs-internal/mcp-architecture.md` lists `list_calls`. A short calls section goes into
  the getting-started guide for the assistant.

## Decisions

Decided by Dmytro:

- Calls can be browsed and found: newest first, search by phone number or call ID,
  filters for agent, result, category, period and source, and callers as the last four
  digits (2026-11-11, `frontend/CLAUDE.md`).
- The deepest view is a single call (2026-11-12): roadmap 10.08.
- Callers' details are blurred on screen for the video (demo check, 2026-11-13). The last
  four digits already help.

Proposed by Claude:

- One web route and one MCP tool with the same filters.
- Rows do not open until the single call exists.
- The Source filter waits for simulated and test calls.
- Search: digits match the end of the number; anything else matches a call id.

## Answered questions

Dmytro accepted the recommendations ("Accept, build", 2026-11-13):

1. Each call shows its result and worst finding, with the Failed, Degraded and Clean
   tiles and the Result and Category filters.
2. The backend of "Search calls by phone number or call ID" (feature 12) is folded in,
   and feature 12 closes with this pull request.
3. The Source filter and the "Simulated" and "Test" labels wait until such calls exist.

## Done when

- `make check` passes. Backend tests cover:
  - newest first and paging;
  - only the open workspace's calls;
  - the caller as the last four digits, never the full number;
  - each filter and the period;
  - search by the last digits, by a full number, by Connexity's call id and by Retell's;
  - the tiles and the worst finding (with question 1);
  - `list_calls`: the same rows, an unreachable workspace, paging.
- Played through on a running backend through the API and MCP.
- **For Dmytro to check on screen** (app.connexity.ai after merge, the demo workspace):
  - Calls is in the sidebar;
  - the list shows the 78 calls newest first, callers as "•••• 1234", durations;
  - the tiles add up;
  - searching the last four digits of a known caller finds the call;
  - each filter narrows the list, and "Clear" restores it;
  - dark and light both look like the design.

Built on the demo checks branch (#193), which touches the same MCP routes, and rebased
onto `main` once it merges.

## Out of scope

- The single call: recording, transcript, tool calls (10.08). The Issues page (10.09).
- A Calls tab on the agent profile (no agent profile yet).
- Simulated and test calls (question 3).
- Exports, column pickers and saved views (never).

## Risks

- **Search by number** matches the end of the stored number. Numbers stored in odd
  formats may be missed; the tests cover E.164 and the formats Retell sends.
- **The worst finding** reads as the check's title and key, which is plain but not the
  design's hand-written sentence ("Transfer to the front desk dropped the call"). Better
  sentences come with the issue type library.

## Outcome

### Deviations from the plan

- **A call's result now counts every finding,** including one from a check added after
  the call. Before, those were "retroactive" and counted for nothing (slice 2.3). The
  Calls page would have shown the demo agent's 78 calls all clean while `list_issues`
  showed 13 and 4. Dmytro decided: "whats the difference when we found issue immediately
  or next year its still an issue, especially because the product algorithms will
  evolve. The only risk is to show it in future because it was already resolved but then
  its another problem. So yes count them" (2026-11-13).
  - This applies everywhere a result is computed (`call_check_statuses` and the calls
    list).
  - Findings stay marked retroactive, for anything that must leave them out later.
  - **One test changed to the new rule:** `test_a_call_is_failed_degraded_clean_or_unchecked`
    now expects a call checked by a later check to be failed (it expected clean).
- **"Show more" grows the page** (25, 50, …) in the address, so a refresh keeps it. The
  web route takes `skip` and `limit`; MCP takes a cursor.
- **The shared NumberTile** imported `severity` through a path the UI package's export
  map does not cover (only `.tsx`). It is the first time the app uses the tile, so the
  import is now relative.
- **The worst finding reads "Title: key",** for example "Booking with missing or
  placeholder details: schedule_appointment".

### Check results

`make check` on the final tree: see the table below. `pnpm build` also succeeds, with
`/calls` among the routes.

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

New tests (`test_calls_list.py`, 12):

- newest first, the caller as four digits and never the full number, the duration, the
  result and the worst finding with how it was found;
- the period;
- the agent, result and category filters, with the result filter leaving the tiles;
- search by the last digits and by a full number in three formats;
- search by Connexity's id and by Retell's;
- a search with no match;
- paging;
- another workspace;
- the web route for the open workspace, with its filter options.

MCP server: `list_calls` is listed as read-only and sends its search and filters.

**Played through on a running backend** (port 8025, local database), with 30 invented
calls on one agent: 7 with booking problems, and callers `+1732555` plus 1000 to 1029.

| # | Request | Came back |
|---|---|---|
| 1 | `GET /calls` | Tiles 30 / failed 7 / clean 23; 25 rows, more to show; newest first, "••••1000", the worst finding |
| 2 | `result=failed` | 7 rows; tiles unchanged |
| 3 | `q=1009` | The one call, "Two bookings for one slot" |
| 4 | `period=7d` | 24 calls, 5 failed |
| 5 | `category=booking` | 7 calls |
| 6 | `limit=50` ("Show more") | All 30, no more |
| 7 | Any answer containing a full number | None |
| 8 | Not signed in | 401 |
| 9 | MCP `list_calls`, query "+1 732 555 1009" | The one call, failed; guide `connexity://guides/calls` |

The backend log had no errors.

`/code-review` (high) raised three findings:

- **Phone search scans every caller number** with a regular expression, so it cannot use
  the index. That is fine at today's size; a stored digits-only column fixes it later.
  Not fixed.
- **The tiles leave out unchecked calls:** the design has four tiles, so an unchecked call
  is in "Calls" and nowhere else. Not fixed.
- **Every finding now counts:** Dmytro's decision, recorded above.

**For Dmytro to check on screen** (app.connexity.ai after merge, in the demo workspace):

1. **Calls** is in the sidebar and opens the page in dark and light, matching the design.
2. The tiles read Calls 78 (in the last 30 days), with Failed showing the calls the two
   booking checks found. They add up with Clean, unless some calls are unchecked.
3. The list is newest first: "Today 09:42" style times, "Front desk"-style agent names,
   "•••• 1234", durations as 1:13, Failed in colour, Clean quiet, and the worst finding.
4. Typing the last four digits of a caller and pressing Enter finds the call; a Retell
   call id finds it too.
5. Agent, Result and Category each narrow the list; "Clear" restores it; "No calls match"
   offers to clear.
6. The period picker changes the tiles and the list. "Show more" adds 25.
7. Rows do not open yet: the single call is next (10.08).

### Not done

- **The single call** (10.08). Rows don't open.
- **The Source filter and the Simulated and Test labels:** no such calls yet.
- **Hiding issues already resolved** from past calls' results: Dmytro called it "another
  problem", for later.
- **Throwaway data in the local dev database:** one more play-through user with 30
  calls.
