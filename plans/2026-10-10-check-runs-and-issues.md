# Check runs, issues and call status

- **Owner:** Dmytro
- **Slice:** 2.3

## Goal

Three things are true after this merges that are not true now:

- For every call it is known what each check did on it: ran, was skipped because the
  call lacks what the check needs, broke, or was switched off.
- Every finding belongs to an issue: all findings with the same symptom on one agent. A
  person can resolve an issue or accept it as known, and a failure after a resolution
  shows as a regression.
- A call is failed, degraded, clean or unchecked.

This is foundation for incidents and reliability (slice 2.4). No check is added: the
library stays at "tool call failed".

## Changes

**What each check did on each call**

- A new table holds one row per call and check: the check's version, when, and the
  outcome: ran, skipped, broke or off. A skipped row says what the call was missing.
- A check declares what it needs from a trace. "Tool call failed" needs tool results:
  every tool call in the trace has a status. A call without them is skipped for that
  check, and its earlier findings from that check are removed, because the trace they
  pointed at was replaced.
- "Checked at" on a call stays, and now means the last time the checks were run on it.

**Checks that never ran on a stored call**

- A stored call with no row for a check is checked in the background, in the pass that
  already looks up executions when an agent's calls are opened, up to 200 calls a pass.
- `POST /agents/{id}/checks/run` does the same on request, for the assistant.
- Findings on calls that started before the check existed are retroactive, as decided.
- A call that already has a row is not run again by this pass, whatever its outcome and
  whatever version ran. Sending the call again still checks it afresh.

**Issues**

- A new table. An issue is identified by agent, check type and key (for the one check,
  the tool's name). A finding joins its issue when it is stored; the issue is created
  if it does not exist.
- An issue is open, resolved, regressed or accepted. It is never deleted by the product.
- A person resolves an issue (optionally naming the version that carried the fix),
  accepts it as known, or reopens it. Each is a decision record. Accepting requires a
  reason.
- A resolved issue becomes regressed when a finding is stored on a call that started
  after the resolution. A finding on an earlier call that arrives late does not regress
  it. An accepted issue stays accepted.
- When an issue was first and last seen, and how many findings and calls it has, are
  worked out from its findings, not stored.

**Call status**

- Failed: at least one finding whose effect was "fails". Degraded: findings, none of
  those. Clean: at least one check ran and nothing was found. Unchecked: no check ran
  on it (never checked, or every check was skipped, broke or was off).
- Retroactive findings do not count.
- Worked out from the findings and the run rows each time; not stored on the call.

**API**

- `GET /agents/{id}/issues`: the agent's issues with state, counts, first and last seen.
- `GET /issues/{id}`: one issue with its findings and the calls they are on.
- `PUT /issues/{id}/state`: resolve, accept or reopen, with a reason.
- `POST /agents/{id}/checks/run`: check stored calls a check never ran on.
- A call in the list and the call detail gain `check_status`.
- The call trace response gains each check's outcome, and each finding its issue.
- One migration. The generated client is regenerated.

## Decisions

Made by Dmytro on 2026-10-10:

- Checks are a library that grows only when he asks. This slice adds none.
- Slice 2.2 is folded into this work ("Fold").
- Incidents close only manually. (Affects slice 2.4; here it removed the need for any
  "passing call" evidence.)

Proposed by Claude; Dmytro agreed to the three together ("Agree"):

- Split the old 2.3 in two; this is the first half.
- A call that fails for two issues belongs to both incidents (slice 2.4).
- "After" a resolution or a close goes by when the call started; versions are not
  ordered to decide a regression.

Proposed by Claude, not put to Dmytro:

- Dmytro agreed to the draft of the whole old 2.3 and its questions, not to this plan
  file as such. Which done-when lines belong to this half is Claude's split.
- A fourth outcome, "off", is recorded, so a call checked while a check was switched off
  is not picked up again as never checked.
- A call where no check ran is "unchecked", a fourth status beside failed, degraded and
  clean.
- "Tool call failed" needs every tool call to have a status. A call where one tool call
  has a status and another does not is skipped whole.
- A reason is required to accept an issue, optional to resolve or reopen it.
- A new version of a check does not run over stored calls by itself.
- 200 calls per background pass.

## Done when

Played through the API on a throwaway agent with invented calls:

- Three calls with the same tool failing give one issue with three findings on three
  calls, open. A call failing on another tool gives a second issue.
- The failing calls are "failed"; a call whose tool call succeeded is "clean".
- A call whose tool call has no status has the check recorded as skipped, with what was
  missing, and is "unchecked".
- Resolving the issue stores a decision record. A later failing call makes it
  regressed; a failing call that started before the resolution does not.
- Accepting without a reason is refused. An accepted issue stays accepted when a new
  finding arrives.
- A stored call that no check ran on is checked by `POST /agents/{id}/checks/run`, and a
  second request finds nothing left to do.
- Another company cannot read or change an issue.

And:

- With the check switched off, the call records "off" and is "unchecked".
- A check that breaks is recorded as broke for that call.
- On the local real calls: how many calls got a run row from the background pass, and
  the count of each status. Counts only.
- `make check` passes.

## Out of scope

- Incidents, reliability and quality (2.4). Any screen (2.5). MCP tools (1.8).
- Any new check, fact or threshold.
- Dismissing a finding as wrong. Merging or splitting issues.
- Filtering the call list by status.
- Re-running a check over history when its version changes.

## Risks

- **Nothing real will become an issue.** The connected agents have no failed tool call.
  The slice is proven on invented calls unless the fault agent is set up.
- **A call that is partly unjudgeable is skipped whole** (one tool call with a status,
  one without). A visible failure on such a call is not raised.
- **Call status is worked out on every read.** Fine for a page of calls; a count of
  failed calls over a long period (slice 2.4) may want it stored.
- **The issue table is shaped before incidents exist.** Slice 2.4 may add to it.
- **Any signed-in user or token of the company can resolve or accept an issue**, as with
  check settings.
- **A reviewer should push back if** "unchecked" as a fourth status, beside the three in
  the vision, is one too many.

## Outcome

### Deviations from the plan

- **A stored call that cannot be checked at all is recorded as broke.** The plan covered
  one check breaking, not the whole run failing (a stored trace that no longer reads,
  for example). Such a call had no row, so every pass would have picked it up again and,
  with enough of them, never reached the calls behind. Found in review.
- **The background pass runs in a worker thread.** The plan put it "in the pass that
  already looks up executions". Run there it would have held up every other request for
  the length of the pass, about five seconds for 200 calls. Found in review.
- **"Checked at" is now set even when a check broke.** In slice 2.1 a broken check left
  it empty. What each check did is in the run rows now, so the time only says when the
  checks were last run.

### Check results

`make check` on this branch:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 12s |
| Backend tests and coverage | ok | 119s |
| MCP server tests | ok | 3s |
| Frontend lint | ok | 11s |
| Frontend types | ok | 9s |
| Generated client is fresh | ok | 11s |

All steps passed in one run, after the review fixes. 12 backend tests are new.

Through the API, against the running local server and the local database, on a
throwaway agent with invented calls:

| Request | Expected | Came back |
|---|---|---|
| Ingest 3 calls failing on one tool and 1 on another; `GET /agents/{id}/issues` | 2 issues; the first open with 3 findings on 3 calls | As expected |
| `GET /calls/{id}` for a failing call, a succeeding one, one with no tool status | failed, clean, unchecked | failed, clean, unchecked |
| `GET /calls/{id}/trace` for the call with no tool status | The check skipped, missing `tool_results` | As expected |
| `GET /issues/{id}` | 3 findings, on the 3 calls | As expected |
| `PUT /issues/{id}/state` resolved, with a version | 200, resolved, version kept | As expected |
| Ingest a failing call that started before the resolution | Still resolved, 4 calls | resolved, 4 calls |
| Ingest a failing call that started after it | Regressed, 5 calls | regressed, 5 calls |
| `PUT` accepted with no reason | 422 | 422 |
| `PUT` accepted with a reason, then a new failing call | 200; stays accepted, 2 calls | As expected |
| `PUT` state regressed | 422 | 422 |
| `GET /agents/{id}/decisions` | 2 records of kind `issue_state` | As expected |
| `POST /agents/{id}/checks/run` with nothing left | checked 0, remaining 0 | As expected |
| `GET` an issue that does not exist; `GET` an issue without logging in | 404; 401 | 404; 401 |
| `GET /agents/{id}/calls` | A `check_status` on every call | 7 failed, 1 clean, 1 unchecked |

Not reachable over HTTP, so covered by the test suite only: a stored call that was never
checked (the ingest endpoint always checks), another company's attempt, a check switched
off, a check that breaks. The throwaway agent and its 9 invented calls were removed
afterwards, directly in the local database.

Real calls, on Dmytro's machine, counts only:

| Measure | Result |
|---|---|
| Stored calls with no run row before | 813 (597 and 216) |
| Passes of 200 needed | 3 and 2 |
| Left afterwards | 0 |
| Time | 18 seconds in all, about 22 ms a call |
| Run rows | 813 ran, 0 skipped, 0 broke |
| Calls by status | 813 clean |
| Findings, issues | 0, 0 |

Migration `0009_check_runs_and_issues` applies, reverses and re-applies on the local
test database, and `alembic check` reports no drift. Its step that gives existing
findings an issue was tried with three seeded findings on two keys: two issues, no
finding left without one.

**`/code-review`** was run on the diff before the fixes. Six findings:

| Finding | Outcome |
|---|---|
| The background pass blocked every other request while it ran | Fixed: worker thread |
| A call that cannot be checked at all was retried on every pass | Fixed: recorded as broke |
| A typed database expression was declared as `Any` | Fixed |
| Finding calls that lack a run row looks at every call of the agent, each time its list is opened | Not fixed; see Not done |
| A call that used no tool, from a mapping that does not say whether it reports tool calls, stays unchecked | Not fixed; see Not done |
| The issue list has no limit and is sorted in memory | Not fixed: bounded by tools times checks today |

The review was done by the session that wrote the code, not an independent reviewer.

### Not done

- **Nothing was looked at in a browser.** There is no screen in this slice; nothing for
  Dmytro to check on screen.
- **Nothing real became an issue.** As the plan's first risk said, the connected agents
  have no failed tool call. Every behaviour is proven on invented calls.
- **"Is anything unchecked?" is asked of every call of the agent each time its list is
  opened** and the last sync is over 15 seconds old. Quick at 813 calls; it will need a
  cheaper test at a hundred thousand.
- **A call is unchecked when its mapping does not say whether it reports tool calls and
  the agent called none.** That follows the published meaning of "tool results", and it
  is honest, but for such a mapping most calls will read "unchecked". The connected
  provider's mapping does say, so none of the 813 is affected.
- **A new version of a check does not run over stored calls**, as the plan said.
- **Root `CLAUDE.md` gains two rules in this pull request**, at Dmytro's request on
  2026-10-10: checks are a library that grows only when he asks, and every reply ends
  with his next step. The vision and `REBUILD.md` record the day's decisions: manual
  closing of incidents, "at least one incident", slice 2.2 dropped, the old 2.3 split.
- The local development database was migrated to `0009`, and its 813 calls now have a
  run row each.
