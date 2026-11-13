# Two demo checks, with severity

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Test what we can find now (three demo checks,
  with severity)" (10.06, Stage Check). It folds in "Critical and warning defaults"
  (10.04).
- **Design:** No UI change.
- **MCP:** proposed `list_issues(workspace_id)` (question 2); otherwise none.

## Goal

Connexity finds two of the three problems the demo shows, on any agent, from the calls
alone, with deterministic rules. Both are Critical by default. Run over the synced calls,
each finds its issue on the demo agent's real calls. The demo check counted 11 of 27
bookings and 4 calls, so each issue should show "in N of 78 calls".

**The third, "A change confirmed without a tool", moves to model-based checks**
("Classifiers and judges", 10.16). A phrase rule is not good enough for it, and whether it
is a trained classifier or an LLM is still to be decided (Dmytro, 2026-11-13).

The three checks were named by Dmytro on 2026-11-13 (roadmap entry):

1. **Booking with missing or placeholder details:** the booking tool was called with an
   empty or placeholder name, street address or zip ("{{...}}", "[... pending]",
   "00000", "").
2. **Two bookings for one slot:** the booking tool was called twice in one call for the
   same time.
3. **A change confirmed without a tool:** the agent told the caller an appointment was
   cancelled or moved, with no tool call that could do it. Moved to 10.16 (see Goal).

## What exists today

- **Checks are pure code over a call's trace:** its utterances (speaker, text) and tool
  calls (name, arguments, status). There is no model and no network, and every call is
  checked on arrival and when a check is new (#192).
- **One check exists,** "Tool call failed", which fails the call (Critical).
- **Severity is the check's mode:** "fails the call" is Critical, "flags it" is a Warning
  (`docs-internal/checks-and-incidents.md`). Each check has a default mode, and a person
  can change it per agent.
- **No issue type library exists yet** (roadmap feature 23, not in the Demo milestone).

## Changes

### How each check finds its issue: both are deterministic rules

Neither uses a model. Each is plain code over the call's stored trace, so the
same call always gives the same answer, it costs nothing to run, and a finding points at
the exact tool call or sentence it came from. Every check already carries how it finds
things (`CheckKind`: `rule`, `classifier` or `judge`), and so does every finding. This
plan surfaces it:

- **The issue type library** lists each check as "Rule (deterministic)" or "Model".
- **`list_issues`** answers `found_by: rule` or `model` for each issue (question 2).

| Check | Found by | What it reads |
|---|---|---|
| Tool call failed (exists) | Rule | The status of each tool call |
| Booking with missing or placeholder details | Rule | The booking tool's arguments |
| Two bookings for one slot | Rule | How often the booking tool was called, with its time argument |
| A change confirmed without a tool | Model (later, 10.16) | Not in this feature |

### Which tool books, and which can change a booking

The checks must work on any agent, so they cannot name the demo agent's tools. A check
sees each tool call's name. Proposed (question 1):

- **A booking tool** has a name that says it books: `book`, `schedule`, `appointment`
  or `reserve`. A name that also says it only looks (`availab`, `slot`, `get`, `list`,
  `find`, `check`) or changes (`cancel`, `reschedul`) is not one.
  `schedule_appointment` books; `get_availability_calendar_slots` does not.

The finding's detail names the tool it judged, so a wrong judgement is visible.

### The two checks (backend)

Each is a pure rule in `app/services/checks/rules/` with its title, category and
default. Both default to "fails the call", so they are Critical.

1. **`booking_details_missing`**, "Booking with missing or placeholder details",
   category Booking.
   - **What it finds:** each call to a booking tool whose argument for a name, street
     address or zip is empty or a placeholder. Those are arguments whose name contains
     `name`, `address`, `street`, `zip` or `postal`.
   - **What counts as a placeholder:** template braces (`{{...}}`), a bracketed note
     (`[address pending]`, `[unknown]`), a run of zeros (`00000`), or text such as
     `missing`, `pending`, `unknown`, `tbd` or `n/a`.
   - **The finding:** key is the tool's name; detail is the argument names that were
     empty or placeholders, never their values.
2. **`booking_duplicated`**, "Two bookings for one slot", category Booking.
   - **What it finds:** a booking tool called twice or more in one call, without error,
     with the same value for its time. The time argument is the first whose name
     contains `time`, `date`, `slot` or `start`.
   - **The finding:** key is the tool's name; it points at the second booking and every
     later one.

### Defaults recorded in an issue type library

A short `docs-internal/issue-types.md` (question 3) lists every check: its type, title,
category, default severity, what it finds, its key and its known limits. It covers the
two new checks and "Tool call failed" (stays Critical). It's the start of the library
in feature 23, and a test fails when a registered check is missing from it.

### Running them over the synced calls

- **Production checks them on its own after merge.** The minute pull checks stored calls
  that new checks have never run on (#192), so within a few minutes of deploying, every
  synced call has been checked by all three.
- **Before merge, I measure them against production.** I read production read-only, run
  the three checks in memory over every synced call's trace, and write nothing. The
  Outcome gets counts only, per check and per workspace: findings, calls, and "in N of M
  calls". No call content goes into the repo or the pull request.
- **Dmytro reviews a sample** to judge precision. I prepare it outside the repo: the
  calls each check flagged, with the utterance or tool name involved, for you to look
  at.

### MCP (question 2)

The assistant cannot see issues through MCP yet; the Issue page features add that.
Proposed: a small `list_issues(workspace_id, agent_id?)` now. It returns each issue's
type, title, category, severity, calls affected "N of M", state and first and last
seen, worst first. Each issue also says how it was found (`found_by: rule` or `model`). Then the demo
assistant can say "3 critical issues" on real data.

## Decisions

Decided by Dmytro (roadmap entry, 2026-11-13):

- The checks and their definitions; Critical by default; "Tool call failed" stays
  Critical.
- Only checks 1 and 2 now. "A change confirmed without a tool" moves to model-based
  checks; classifier or LLM is to be decided (2026-11-13).
- Run them over the synced calls, and report counts per issue type and workspace, never
  call content.
- Dmytro reviews a sample for precision.

Proposed by Claude:

- Tools are recognised by their names, so the checks work on any agent.
- The issue type library starts as a short doc with a test.
- A small `list_issues` MCP tool.

## Answered questions

Dmytro accepted the recommendations ("Accept, build", 2026-11-13):

1. The booking tool is recognised by its name.
2. `list_issues` is added to MCP now.
3. The issue type library starts as a short doc in `docs-internal/`, with a test that
   every check is in it.

## Done when

- `make check` passes. Tests with invented traces:
  - each check finding its problem, and not finding it in near-misses: a full booking,
    two bookings at different times;
  - placeholders and empty values;
  - tool roles from names;
  - the details never holding values;
  - defaults all Critical;
  - every check in the issue type doc;
  - `list_issues`, if accepted.
- **Measured against production read-only, before merge:** each check's counts on the
  demo agent's 78 calls, compared with the demo check (11 of 27 bookings, 4 calls). Differences are explained in the Outcome.
- **After merge, on production:** within minutes the findings exist, and the issues show
  "in N of 78 calls". Dmytro reviews the sample.

## Out of scope

- Model-based checks, including "A change confirmed without a tool" (10.16). Tool roles
  declared by the assistant (question 1).
- Screens for issues.
- Checks beyond these three (checks are a library: Dmytro names each).

## Risks

- **Names that do not say what a tool does** (`tool_1`) make checks 1 and 2 see no booking
  tool, so they find nothing rather than something wrong.
- **Real call content** is read from production to measure; only counts leave my
  scratchpad, and the sample stays outside the repo.

## Outcome

### Deviations from the plan

- **The details check finds 13 of 78 calls, not the demo check's 11 of 27 bookings.** The
  two extra calls are true positives that the demo check's simpler test missed: one
  booking's zip was the text "null", another's name was "Unknown".
- **Issues carry severity and how they were found.** The issue summary gains `critical`
  (any finding fails the call) and `kind`, both read from the findings.
- **Single-check tests were given a one-check setup.** These are four tests about call
  status and the check engine, plus the catch-up pass's tests. They now set "Tool call
  failed" as the only check, and two others filter the runs to the check under test.
  With three checks, a call that one check skipped or was switched off for is still
  checked by the others, so it is "clean", not "unchecked". Nothing they assert was
  loosened.

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

- `test_booking_checks.py` (25, invented Retell calls):
  - booking tools known by name;
  - both checks are rules, Critical, under Booking;
  - every kind of empty or placeholder value;
  - details naming arguments, never values;
  - full bookings and non-booking tools not flagged;
  - each booking judged on its own;
  - two and three bookings of one slot;
  - different times, failed bookings and the time zone not flagged.
- `test_mcp_issues.py` (4, real engine):
  - `list_issues` worst first, with severity, `found_by`, category and "N of M";
  - one agent;
  - paging;
  - no issues;
  - another workspace or agent not found.
- `test_issue_types_doc.py`: every registered check is in
  `docs-internal/issue-types.md` with its title, found by and default.
- MCP server: `list_issues` is listed as read-only, sends the agent, and keeps
  `found_by`.

**Measured on production, read-only, before merge.** Every session was set read-only
and verified before a query, and nothing was written. The three checks ran in memory
over every synced call's trace. Counts only:

| Workspace | Check | Found by | Calls | Findings |
|---|---|---|---|---|
| Workspace 1 (78 calls with a trace) | Tool call failed | Rule | 0 of 78 | 0 |
| | Booking with missing or placeholder details | Rule | 13 of 78 | 13 |
| | Two bookings for one slot | Rule | 4 of 78 | 4 |

The demo check expected 11 of 27 bookings and 4 calls. Two bookings had placeholder
values the demo check did not test for (see above). Both checks find their issue on
the demo agent's real calls.

**For Dmytro's precision review:** the 17 findings (13 and 4) are in a private file
outside the repo. Each has its Retell call id, the tool and the argument names, never
the values.

`/code-review` (high) raised four findings, all left as they are:

- **Placeholder words can match a real value,** for example a street called "Pending
  Lane".
- **Some tools look like booking tools by name,** for example `confirm_appointment`.
- **"Clean" now covers calls only the booking rules ran on.** A call with no tool
  results is clean rather than unchecked.
- **`list_issues` pages in memory.**

The first two are recorded as known limits in `docs-internal/issue-types.md`.

**After merge, on production:** within a few minutes, the minute pull checks every stored
call with the two new checks. `list_issues` then shows "Booking with missing or
placeholder details, critical, rule, in 13 of 78 calls" and "Two bookings for one slot,
critical, rule, in 4 of 78 calls".

### Not done

- **"A change confirmed without a tool"** moved to model-based checks (10.16).
- **Tool roles declared by the assistant** (answered: names for now).
- **A screen for issues.**
