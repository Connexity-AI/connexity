# Check every call: on arrival, and the calls that came before

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Check every new call on arrival" (10.03,
  Stage Check). Already built in part (slice 2.1): this reviews it against continuous sync
  and fills the gaps.
- **Design:** No UI change.
- **MCP:** none needed. Checking happens on its own; what checks find reaches the
  assistant with the issue tools of later features.

## Goal

Every call is checked by every current check, however it arrived and whenever the check
was added or changed. That covers new calls within a minute of arriving, calls stored
before a check existed, and calls checked by an older version of a check.

"Every new call is checked as soon as it arrives through continuous sync, and calls
synced before a check existed are checked too." (roadmap entry)

## What exists today (reviewed)

**On arrival: every path checks.** Each path below stores the call and then runs
`check_call_safely`, which checks it with every current check and never fails the store:

| How a call arrives | Checked on arrival |
|---|---|
| The scheduled pull (`call_pull.py`, every minute) | Yes, through `store_retell_calls` |
| Its re-read for late analysis | Yes: the trace is replaced and checked again |
| The webhook, where set | Yes |
| The first scan (`scan_calls`) | Yes, through `store_retell_calls` |
| The ingest route (SDK traces) | Yes |
| Executions found later in n8n | Yes, checked again with them |

**The gaps:**

1. **Calls stored before a check existed are never checked on their own.** The pass that
   finds them (`check_unchecked_calls`) runs only when the 1.x calls page is opened
   (deleted) or through `POST /agents/{id}/checks/run`. So a check added in a deploy never
   reaches the calls already in the database. (`REBUILD.md`: "calls stored before the
   check engine are unchecked until they are sent again".)
2. **A new version of a check does not run over stored calls.** A call counts as checked
   once it has any run of that check, whatever its version. (`REBUILD.md`: "a new
   version of a check does not run over stored calls".)
3. **A call a check broke on is never retried.** It is recorded as "broke" and counts as
   checked. (`REBUILD.md`: "a call a check broke on is not retried".)

## Changes

- **The scheduled pull also checks the calls that need it.** After its new calls and
  re-reads, each run uses the rest of its time to check stored calls of added agents that
  need checking, newest first. It stops at 200 calls or when its time budget ends.
  Checks are code with no network, so this is quick. A backlog drains over a few
  minutes, and from then on each run finds nothing to do.
- **"Needs checking"** means the call has no run of a current check, or a run by an
  older version of it. That covers a new check and a new version of a check (gaps 1 and
  2). A fix to a check that broke ships as a new version, so the calls it broke on are
  checked again with the fix (gap 3). A call is never checked twice by the same version.
- **Findings from these passes are marked retroactive** when the call started before the
  check existed, as today. A call checked again by a new version keeps its issue: the
  identity does not depend on the version.
- **`POST /agents/{id}/checks/run`** uses the same "needs checking" rule.
- **Each run's log line** adds `calls_checked`.

## Decisions

Decided by Dmytro (roadmap entry):

- Every new call is checked on arrival through continuous sync. Calls synced before a
  check existed are checked too.

Proposed by Claude:

- The pull's minute run drains the check backlog, so it needs no new scheduler job.
- A new version of a check re-runs over stored calls, and that is also how a call a check
  broke on is retried.
- Delete the 1.x page trigger.

## Answered questions

Dmytro accepted the recommendation ("Accept, build", 2026-11-13):

1. A new version of a check re-runs over every stored call, so issue counts match what
   the check says now.

## Done when

- `make check` passes. Backend tests cover:
  - every arrival path leading to a check: the pull, its re-read, the webhook, the first
    scan;
  - a pull run checking calls stored before a check existed, marked retroactive;
  - a new version of a check re-running over stored calls, and not twice;
  - a call a check broke on, checked again by the next version;
  - the 200-call cap and the time budget, with the backlog finished over runs;
  - `GET /agents/{id}/calls` no longer syncing or checking.
- Built on top of the categories branch (#191), which touches the same check code;
  rebased onto `main` once #191 merges.
- Played through on a running backend with Retell's answers invented: stored calls with
  no check runs are checked by the next pull run; a version bump re-checks them once.
- **After merge, on production:** the pull's log shows `calls_checked`. The production
  agent's 78 calls already have a run of `tool_call_failed` version 1, so nothing is
  re-checked until a check changes.

## Out of scope

- New checks, including the demo's three issues: booking with missing or placeholder
  details, two bookings for one slot, a change confirmed without a tool. They belong to
  "Test what we can find now" (10.05), and Dmytro names each check (checks are a library).
- Checks that call a model (judges), which are slow and cost money: their own feature.
- Showing what was checked on screen.

## Risks

- **A heavy future check** could make a run's backlog pass slow. The time budget bounds
  it, and judges get their own path.
- **A version bump re-checks every call of every agent,** which takes a few minutes at
  200 per minute for thousands of calls. Issue counts change as it goes.

## Outcome

### Deviations from the plan

- **The 1.x calls page trigger is kept.** Deleting it failed 10 tests and showed that the
  same trigger also retries version resolution and n8n execution lookups, which have no
  other trigger. It now uses the new version-aware pass. Moving those retries into the
  pull is its own work (see Not done).
- **A pass that found nothing is not repeated** until the checks change, or for 10
  minutes. New calls are checked on arrival, so the minute pull no longer scans every
  stored call for nothing (from the review). The memory is per process, so another
  instance may look once more.
- **Recording a call as broke now replaces a run by an older version.** Without that, a
  call that cannot be checked at all would need checking forever and sit at the front of
  every pass.
- **`check_unchecked_calls` became `check_calls_needing_it`,** which takes several agents
  and a deadline. The crud queries became `calls_needing_checks` and
  `count_calls_needing_checks`, which take the current versions.
- **Built on the categories branch (#191)** and rebased onto `main` after it merged.

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

New tests (`test_check_every_call.py`, 8):

- calls stored before a check existed are checked, once;
- a new version of a check runs over stored calls, once;
- a call a check broke on is checked again by the next version;
- a call that cannot be checked at all is recorded as broke by the current version and
  not picked up again;
- a pass stopping at its limit (newest first, the rest next time) and at its deadline;
- the minute pull checking calls that need it;
- an empty backlog not looked at again until the checks change.

`test_call_pull.py` now also checks that calls the pull stores are checked on arrival.
The webhook's tests already check that for the webhook. The first scan and the re-read
store through the same function as the pull.

**Played through on a running backend** (port 8024, local database). The setup was 5
calls stored with no check runs (3 with a failed tool call), the pull route called with
a locally signed token, and a version bump made inside the server:

| # | Step | Came back |
|---|---|---|
| 1 | Before | No check runs on the 5 calls |
| 2 | A pull run | 200, `calls_checked` 10 (the 5, plus older local calls); the 5 have version 1 runs |
| 3 | Another run | `calls_checked` 0 |
| 4 | Version 2 ships, a run | `calls_checked` 199: every local call, newest first, 200 at most per run |
| 5 | Another run | `calls_checked` 200, still draining the local backlog |
| 6 | The agent's issues | One `tool_call_failed` issue under Tools and integrations, with 3 findings |

One local call from an earlier play-through could not be checked. It had been edited by
hand to end before it started. The engine logged it and recorded it as broke, as
designed.

`/code-review` (high) raised five findings. Fixed:

- the minute scan over every call;
- a call that cannot be checked being picked up forever;
- deleting the page trigger, which would have dropped other retries.

Not fixed:

- **Version and execution retries have no live trigger** in production: their only
  trigger is the 1.x calls route, whose screen was deleted in M1.1. That predates this
  change.
- **The catch-up pass goes newest first across all workspaces,** so one workspace's
  backlog can delay another's older calls by a few minutes.

**After merge, on production:** each `call_pull` log line shows `calls_checked`. The
production agent's 78 calls already have version 1 runs, so the first pass finds
nothing, and later passes are skipped until a check changes.

### Not done

- **Retrying unresolved versions and missing n8n executions automatically,** for
  example from the minute pull. Today only the 1.x calls route triggers it.
- **The demo's three checks** are "Test what we can find now" (10.05).
- **Throwaway data in the local dev database:** one more play-through user with 5 calls.
