# The check engine

- **Owner:** Dmytro
- **Slice:** 2.1

## Goal

When a call arrives, every check that is switched on for its agent runs over it, and
what it finds is stored as findings that point at exact events in the trace. A person
can set each check per agent to off, flags or fails the call, and every such change is
kept as a decision record.

This is the machinery of Phase 2 (vision, section 7). It ships with one simple check so
that something real runs; the other starting checks are slice 2.2.

## Changes

**Checks**

- A rule check is code: a pure function from a call's trace, its executions and its
  facts to a list of findings. It reads no database, calls no network and no model.
- Each check declares its type, a version (a number raised by hand when its logic
  changes), its default setting, and the key of each finding it raises (for the first
  check, the tool's name).
- A registry lists the built-in checks. Nothing in the engine names a provider or a
  backend.
- The first check is **tool call failed**: a tool call whose status in the trace is
  error or timeout. It fails the call by default. Reading the execution's status as well
  is slice 2.2.

**Facts**

- A fact is a value derived from the trace and attached to one or more events, produced
  by a named, versioned function. A check names the facts it needs.
- Facts are computed in memory for each run and are not stored. No fact ships in this
  slice; the interface is exercised by tests only.

**Findings**

- A new table. A finding holds its call, agent, check type, check version, key, the ids
  of the events it points at, a small structured detail, and the effect it had.
- Events are named by their id in the trace, not by row, because sending a call again
  rewrites its event rows.
- A finding copies nothing a party said and no tool argument or result.

**When checks run**

- After a trace is stored, at all three ways in: the ingest endpoint, the provider
  webhook and the pull.
- Again after executions are stored for a call, because they arrive later than the call
  and later checks read them.
- A run leaves the call with exactly the findings the checks raise now: a finding that
  is still raised keeps its row and the time it was first raised; one that no longer
  holds is removed.
- The call records when it was last checked.
- A check that raises an error is logged, and the call is left stored, unchecked, with
  the findings it had.
- Production, test and simulated calls are all checked.

**The past stays as it was**

- A finding's effect (flags or fails the call) is the setting that was in force when
  its call started, read from the decision records. Checking an old call again never
  changes it.
- A check that was off when the call started does not run on that call.
- Connexity records when each version of each check was first present. A finding on a
  call that started before its check existed is stored as retroactive, so later slices
  can show it without counting it.

**Settings and decision records**

- A new decision record table: who, when, what kind of decision, what it applied to,
  the old value, the new value, and a reason. Changing a check's setting is its first
  use; dismissing a finding and resolving an incident will use it later.
- The setting of a check for an agent is its most recent decision record, or the check's
  default when there is none. There is no second table holding the current value.
- A reason is required when a change loosens a check (fails to flags, or anything to
  off), because that can only improve the numbers.

**API**

- `GET /agents/{id}/checks`: the checks with their setting for this agent.
- `PUT /agents/{id}/checks/{type}`: change a setting, with a reason.
- `GET /agents/{id}/decisions`: the agent's decision records, newest first.
- The call trace response gains `findings` and `checked_at`.
- One migration. The generated client is regenerated.

## Decisions

Made by Dmytro on 2026-10-10:

- Approved this plan as drafted in the session ("Ok build").

Proposed by Claude; Dmytro approved them with the plan and did not discuss them one by
one:

- The first check is a real one, "tool call failed" from the trace's status, not a
  check that exists only in tests.
- Facts are not stored in this slice.
- A finding's effect is the setting in force when its call started. A finding from a
  check that did not exist then is retroactive.
- A reason is required on any loosening and optional on tightening.

Proposed by Claude, not put to Dmytro:

- No table for the current setting; it is read from the decision records. The draft
  shown in the session said "a new table for the setting per agent per check". Dropped
  so that there is one source of truth.
- "When a check first existed" is the moment a server that carries it first started
  against the database, kept in a small table.
- A timeout counts as a failed tool call. "No result" does not; it is its own type in
  the vision.
- A finding is the same finding across runs when its check and its events are the same.

## Done when

- An invented trace with a failing tool call, sent to the ingest endpoint, has one
  finding on that event's id, with the check's version, when read back.
- The same trace with the tool call succeeding has none.
- Sending the call again does not duplicate the finding, and the finding keeps its id.
- With the check set to off for the agent, a call that starts afterwards has no finding.
  For another agent it still has one.
- Changing a setting stores a record with who, when, the old value, the new value and
  the reason. A loosening without a reason is refused.
- A finding raised before a setting change keeps its effect when the call is checked
  again.
- A call that started before the check existed gets a retroactive finding.
- A check that raises an error leaves the call stored and unchecked, with a log line.
- A check that asks for a fact receives it.
- Run on the local real calls: how many were checked and how many findings were raised,
  counts only.
- `make check` passes.

## Out of scope

- The other starting checks and the first real facts (2.2).
- Running checks over calls already stored (2.2). Calls stored before this merges stay
  unchecked unless they are sent again.
- Issues, incidents, failed / degraded / clean, reliability and quality (2.3).
- Any screen (2.4) and any MCP tool (1.8). The setting can be changed through the API
  only until then.
- The assistant proposing a setting change for a person to confirm.
- Classifiers, judges, stored facts, findings reported by hand, dismissing a finding.
- Latency (Q9), the fault agent, and the three starting types Dmytro has not confirmed.
  None of them is needed here.

## Risks

- **The run on real calls will probably raise nothing.** Neither connected agent has a
  tool call its provider reports as failed. The machinery is proven on invented traces.
- **Two tables are designed before their main users exist** (issues in 2.3, the screen
  in 2.4). They may need reshaping.
- **Checks run inside the request that stores the call.** That is fine for rule checks.
  Classifiers and judges will need a queue.
- **A setting change does not touch a call already in progress.** A check switched off
  at noon still raises a finding on a call that started at 11:58. That follows from "a
  decision takes effect when it is made", but may surprise.
- **Any signed-in user of the company can change a setting**, and so can anything
  holding that user's token, such as the frozen CLI. "The assistant proposes, a person
  confirms" is not enforced by this slice.
- **A reviewer should push back if** deriving the current setting from the records,
  instead of storing it, looks like it will make slice 2.3's queries awkward.

## Outcome

### Deviations from the plan

- **A check that breaks no longer stops the others.** The plan said the call is left
  unchecked with the findings it had. Review pointed out that one faulty check would
  then leave every call unchecked by every check. Now the broken check is logged and
  keeps the findings it had, the other checks' findings are stored, and the call is not
  noted as checked.
- **Checking a call again only touches findings of the checks that ran.** The plan said
  a run leaves the call with "exactly the findings the checks raise now". That would
  have deleted the findings of a check since removed, and later a judge's or a person's.
  Found in review.
- **A call is locked while it is checked**, with the same lock that storing a trace
  takes, so a slow run cannot write findings from an older trace over a newer one. Not
  in the plan. Found in review.
- **A call whose checks were all switched off still counts as checked.** The plan did
  not say. Only a broken check leaves the checked time empty.
- The plan's API list is as built. `checked_at` on the trace response carries a time
  zone; the column, like the call's other times, does not.

### Check results

`make check` on this branch:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 9s |
| Backend tests and coverage | ok | 81s |
| MCP server tests | ok | 3s |
| Frontend lint | ok | 7s |
| Frontend types | ok | 7s |
| Generated client is fresh | ok | 7s |

All steps passed in one run, after the review fixes. 39 backend tests are new.

Against the done-when:

| Done when | Result |
|---|---|
| A failing tool call sent to ingest has one finding on that event, with the check's version | Yes |
| The same trace with the tool call succeeding has none | Yes |
| Sending the call again does not duplicate the finding, and it keeps its id | Yes; a corrected trace removes it |
| Check off for the agent: a later call has no finding; another agent's still has | Yes |
| A setting change is recorded with who, when, old, new and reason; a loosening without a reason is refused | Yes; refused with 422 for a missing, empty or blank reason, and nothing is recorded |
| A finding raised before a setting change keeps its effect | Yes; a later call gets the new effect |
| A call that started before the check existed gets a retroactive finding | Yes |
| A check that raises an error leaves the call stored and unchecked, with a log line | Yes, and see the first deviation |
| A check that asks for a fact receives it | Yes; derived once per call, and never when no check asks |
| Run on the local real calls | Below |
| `make check` passes | See the table |

Through the API, against the running local server and the local database, on two
throwaway agents with invented calls:

| Request | Expected | Came back |
|---|---|---|
| `GET /agents/{id}/checks` | 200, tool call failed set to fails | 200, as expected |
| Ingest a call with a failing tool call, then `GET /calls/{id}/trace` | One finding on that event, fails, call checked | As expected |
| Ingest a call whose tool call succeeded | No finding, call checked | As expected |
| Ingest the first call again | Same call, same finding id, one finding | As expected |
| Ingest a call that started in 2020 | Finding marked retroactive | As expected |
| `PUT` the check to flags with no reason | 422 | 422, "A reason is required" |
| `PUT` the check to flags with a reason | 200, flags | As expected |
| Ingest the first call again after the change | Its finding still says fails | fails |
| Ingest a new call after the change | Its finding says flags | flags |
| `PUT` to off, then a new call for this agent and for the other | 0 findings and 1 finding | 0 and 1 |
| `GET /agents/{id}/decisions` | 200, two records, newest first, each with who and why | As expected |
| `PUT` a check type that does not exist | 404 | 404 |
| `GET /agents/{id}/checks` without logging in | 401 | 401 |

The throwaway agents and their six invented calls were removed afterwards, directly in
the local database: deleting an agent that has calls through the API answers 500 (see
Not done).

Real calls, on Dmytro's machine, counts only:

| Measure | Result |
|---|---|
| Calls stored | 813, across 2 agents |
| Calls checked | 813 |
| Calls a check broke on | 0 |
| Findings | 0 |
| Time | about 10 seconds, 13 ms a call |
| Tool calls by the status the provider reports | 1,112 ok, 237 no result, 0 error, 0 timeout |

Zero findings is what the plan's first risk predicted. The 237 tool calls with no result
are for slice 2.2: its "tool call got no result" check would raise on them as they
stand, and nobody has looked at whether they are real.

Migration `0008_check_engine` applies, reverses and re-applies on the local test
database, and `alembic check` reports no drift.

**`/code-review`** was run on the diff before the fixes. Eight findings:

| Finding | Outcome |
|---|---|
| Checking again deleted findings of checks that did not run | Fixed |
| A slow run could store findings from an older trace over a newer one | Fixed: the call is locked |
| The current setting was read by the clock instead of from the latest record | Fixed |
| One broken check stopped every check on every call | Fixed |
| A write and a commit per checked call to note the checks that exist | Fixed: one read |
| `checked_at` was sent without a time zone | Fixed |
| The test helper had an untyped parameter | Fixed |
| The "agent or 404" helper is a copy of the one in the tool mapping routes | Not fixed: sharing it means changing a route file outside this slice |

The review was done by the session that wrote the code, not an independent reviewer.

### Not done

- **Nothing was looked at in a browser.** There is no screen in this slice.
- **The webhook and pull paths are tested for "the call was checked", not for a
  finding.** The finding itself is tested through the ingest endpoint, and all three
  call the same function.
- **Two servers deciding at the same instant** are kept in order by a lock on the
  agent, but a record's time comes from the server that wrote it. Clocks that disagree
  by more than the gap between two decisions would put a call that starts in that gap
  under the wrong setting.
- **A call left unchecked because a check broke is not retried.** It is checked the next
  time it is sent or its executions change. Running over stored calls is slice 2.2.
- **Deleting an agent that has calls answers 500.** Found while cleaning up after the
  API run. It is not from this slice: a call points at its agent with nothing saying
  what happens when the agent goes. Noted in `REBUILD.md`.
- **How testing is split is written down in this pull request too**, at Dmytro's request
  on 2026-10-10: the session tests the backend through the API, he tests the frontend
  (`CLAUDE.md`, `frontend/CLAUDE.md`, the lifecycle doc, the plan template). It is not
  part of the slice.
- The local development database was migrated to `0008` by this session, and its 813
  calls now carry a checked time.
