# Fix: Tests tab runs and versions

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Fix: Tests tab runs and versions"
  (10.1991). Fixes what 10.196 (PR #241) and 10.197 (PR #242) built.
- **Design:** No new design. The Tests tab drops its "runs on earlier versions" groups
  for one list, and the Version column gains "· live" and "· not live yet". Dmytro
  checks the screens after merge (no screenshots).
- **MCP:** `get_test_runs` answers the same verdict, version and counts as the tab;
  `run_scenarios` refuses a run whose version cannot be read. Rules, next steps and the
  `contract.py` descriptions follow.

## Goal

Dmytro found these on the Tests tab on 2026-11-19, after PRs #240 to #242:

- a run on version 89, newer than the live 88, shows under "1 run on earlier versions";
- two old runs with no version stored ("latest") count as version 88's;
- calls that stopped with an error are counted as rules that "didn't come up" (20);
- a run whose calls all stopped shows "—" as its result.

The cause: the runner tests Retell's newest version, which can be a draft ahead of the
live one (decided 2026-11-17), while 10.196 took "the current version" to be the live
one and every other version as earlier. After this merges, the tab follows the newest
tested version, lists every run once, and counts only what was judged.

## Decisions

### Decided by Dmytro (2026-11-19, the roadmap row), replacing "the current version is the live version"

1. The verdict follows the **newest tested version**, live or not ("Version 89 · not
   live yet · Failed"), with the live version's state beside it. A full run of a version
   that is not live yet verifies it: the gate tests before going live.
2. Runs with no version stored are **deleted by a migration**; a run can no longer be
   stored without one.
3. **One list of runs**, newest first, no version groups. The Version column says "89 ·
   not live yet", "88 · live", "87".
4. Dmytro tests the screens after merge, no screenshots.
5. Calls that stopped count in **no column**. With no judged call the counts show "—"
   and the Result reads "No result" with the stopped count. `get_test_runs` follows.

### Decided while planning (Dmytro, 2026-11-19)

- With a version picked in the agent page's filter, the list shows **only that
  version's runs**, as the other tabs show only its calls.
- When Retell cannot be read at the start of a run, the run is **refused**: nothing is
  stored, and the answer says to try again.

## Changes

### The version the tab follows

- **The newest tested version** is the highest version number any run of the agent
  tested (Proposed: by number, so testing an older version again does not move the tab
  back). Without runs, the live version.
- **The verdict tile** reads "Version 89 · not live yet · Failed" when that version is
  not the live one, and "Version 88 · Verified" when it is. Its subline gives the live
  version's state: "Live: version 88, verified 19 Nov", or "Live: version 88, not
  verified".
- **With a version picked** in the agent page's filter (10.197), the tab shows that
  version, as today, and the list only its runs.
- `get_test_runs` without `version` answers the newest tested version, with the live
  version's verdict beside it (`live`).

### Every run has a version

- **A migration deletes the runs of scenarios with no version stored,** with their
  simulated calls and verdicts (cascade). In production these are the two smoke runs of
  2026-11-19. 1.x runs (no scope) are not touched.
- **`run_scenarios` reads the version before storing the run** when none is given: the
  agent's newest version on Retell. If Retell cannot be read, the run is refused,
  "Could not read the agent's version on Retell; try again", and nothing is stored. The
  run then always starts with its number.
- A check constraint on the table: a run of scenarios (scope set) has a version.

### One list of runs

- The Tests tab lists **every run of the agent**, newest first, five shown and "Show all
  N runs". The "runs on earlier versions" groups go (`earlier` leaves the API).
- **The Version column** reads "89 · not live yet" for a version above the live one,
  "88 · live", and the bare number otherwise.
- The API gives the live version beside the runs, so the tab can label each.

### Counting only what was judged

- **A run's rules come from its judged calls only.** A rule that only stopped calls
  listed counts in no column; it is not "didn't come up".
- **"No scenario"** stays for spec rules that none of the run's scenarios list.
- **With no judged call** (every call stopped): Passed, Failed, Didn't come up and
  Critical show "—", and the Result reads "No result" with "21 calls stopped" under it,
  for a full run and an on-demand run alike. The run gives no verdict.
- `get_test_runs` totals carry `judged_calls`, and the next steps say a run judged
  nothing.

## Done when

- Route tests through the API (local database), with Retell and the model mocked:
  - a run on 89 while 88 is live: the tab follows 89 ("not live yet"), the live
    version's state is beside it, and both runs are in one list;
  - a full run on 89 with every rule checked and nothing critical verifies 89;
  - `run_scenarios` stores the version it read; with Retell failing, the run is
    refused and nothing is stored;
  - a run whose calls all stopped: no counts, no verdict, "No result", the stopped
    count;
  - a rule listed only by stopped calls counts in no column.
- The migration test: runs of scenarios without a version are gone, 1.x runs stay.
- For Dmytro to check on screen after merge: the verdict tile with a version not live
  yet, the Version column, one list, and a run that judged nothing.

## Out of scope

- The gate itself (Milestone 7): a full run verifies a version not live yet, but
  nothing yet stops a deploy.

## Risks

- Deleting the two production runs removes their simulated calls. They tested nothing
  (every call stopped), and Dmytro decided it.

## Outcome

### Deviations from the plan

- **Calls that stopped count in no column, code checks included.** A run's Critical
  count and the version's `checks` read only the calls a judge read. Findings on stopped
  calls stay on those calls.
- **A rule only stopped calls listed is marked `not_judged`** (`totals.not_judged`,
  `unchecked[].why`). It is in no column, and the Spec tab shows no mark for it. A run
  carries `judged_calls`; with none, it has no result.
- **The run's start no longer pins a version later:** `run_scenarios` reads it first
  (`version_to_test`), so `execute_run`'s pin step and `_pin_version` are gone. The read
  at the start of the run still stores the fingerprint and the tools.
- **The Tests tab lists at most 100 runs,** newest first.
- **The migration is 0039,** after #243's 0038.

### Check results

`make check`, run before the pull request: every step ok (plan, local database, backend
lint and format, pyright, backend tests and coverage, MCP server tests, frontend lint and
types, generated client fresh). One 1.x test that turns a run into a run of scenarios
now gives it a version, as the new check requires (`test_runs.py`).

No separate play-through server: the route tests send the same requests through the API
(`TestClient` on the local database), with Retell and the model mocked:
- a run on 15 while the live version is 14: results and the tab follow 15, a full run
  verifies it, and the live version's state is beside it; both tab and spec read 15;
- one list of runs with the live version for the Version labels;
- `run_scenarios` without a version reads it from Retell and stores it. With Retell
  unreadable it is refused, and nothing is stored;
- a run of scenarios without a version cannot be stored (the check);
- a run whose calls all stopped: no counts in any column, `not_judged` for its rule,
  no verdict, no result, and a "No result" next step;
- the migration deletes a run of scenarios without a version and keeps one with a
  version and a 1.x run, then adds the check back;
- the earlier tests follow: the version is read when not given, and totals carry
  `not_judged` and `judged_calls`.

For Dmytro to check on screen after merge (agent page, Tests tab):
- **A version not live yet:** the verdict tile reads "Version 89 · not live yet · …"
  with "Live: version 88, …" under it.
- **One list of runs,** with "89 · not live yet", "88 · live" or "87" in the Version
  column.
- **A run that judged nothing:** "—" counts, "No result" and "N calls stopped".
- **With a version picked:** only its runs.

### Not done

- None.
