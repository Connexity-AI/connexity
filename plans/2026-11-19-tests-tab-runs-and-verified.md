# Tests tab: coverage, runs and Verified

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Tests tab: coverage, runs and Verified"
  (10.196). Builds on 10.1945 (`plans/2026-11-19-simulations-finish.md`, PR #240): this
  branch starts once that merges.
- **Design:** Claude Design, "Connexity Agent Profile" (Tests and Spec tabs) and
  "Connexity Agent Tests states" (eight states), received 2026-11-19 as "Connexity
  design review (17)"; review (18) left both tabs unchanged and is the copy in the repo. Both screens are copied into `designs/screens/`, and the change
  is written up as `designs/12-adjustments.md` item 32, replacing item 31's tiles,
  "Why it failed" and "All rules". The version filter and "Spec 5 · written for version
  88" in the same screens belong to 10.197 and are not built here.
- **MCP:** `get_test_runs` (the verdict from the version's latest full run, the run that
  decided it, coverage as tests written, checked as rules judged in that run, every run
  with its totals and who ran it) and `run_scenarios` (says whether the run is a full run
  that can verify the version or an on-demand run; a new optional `session_name` input).
  Their `contract.py` entries and input descriptions follow.

## Goal

Dmytro, reviewing the Tests tab on 2026-11-19, replaced how a version is judged:
coverage means tests written, every run is visible in one row with its results, and a
version is Verified only by a full run that checked every spec rule and found nothing
critical. After this merges the Tests tab, the Spec tab and `get_test_runs` all say
the same thing, read from the version's latest full run.

## Decisions

### Decided by Dmytro (2026-11-19, the roadmap row)

1. "Coverage should be that": coverage is tests written, the share of the latest spec's
   rules that at least one active scenario lists.
2. "We should see every run in one row with results and when it affects verified
   version when its partial test, time date and who ran it." No drill-in from the runs
   list.
3. "It should have a test run with all rules checked with results of no critical
   findings": Verified only through a full run (every scenario) in which every spec
   rule was checked (Passed or Failed, not Didn't come up) and nothing critical was
   found.
4. Runs of a set or a pick are on-demand tests and never affect the verdict.
5. Code-check findings read "Found by a code check"; "rule" means spec rules only.
6. "We will see that in Runs table": no separate section explaining the verdict or
   listing warnings.
7. (10.1945) "Verdict only happens when all rules checked": a version with no full run,
   or whose full run judged nothing, has no verdict.

These replace the 2026-11-17 rules that coverage counts rules judged and that a
version's verdict adds up every run, sets and picks included.

### Decided while planning (Dmytro, 2026-11-19)

- A run's Passed, Failed and Didn't come up count **rules**: each rule once per run,
  Failed if any repeat failed it, Didn't come up if no repeat reached it.
- In a full run with every rule checked and nothing critical, non-critical failures
  still give **Verified**; they show in the run's Failed count. The 20% threshold goes.
- "The current version" is the agent's **live version**, the one the agent page shows.
  A new version without a full run reads Not verified, naming the last verified one.

## Changes

### The verdict, read from one run

- **A full run** is a run of `all`. It always takes every active scenario when it
  starts, so it is full by how it starts; no new column (Proposed, instead of the row's
  stored flag: a scenario added later cannot change what the run took).
- **The version's verdict comes from its latest completed full run** and nothing else:
  - **Failed:** a critical rule failed (flaky included) or a critical code check found
    something;
  - **Partially tested:** nothing critical, but some rule of the run's spec was not
    checked (it didn't come up, or no scenario lists it);
  - **Verified:** every rule of the run's spec checked, nothing critical;
  - **Not verified:** no completed full run of this version yet, or one that judged no
    rule. The subline names the last verified version: "Version 88 was verified 19 Nov".
- **Non-critical failures never fail a version.** They show in the run's Failed count;
  the 20% threshold goes.
- `not_tested` becomes `not_verified`, and `partial` is new (`VersionVerdict`).

### A run's totals

- Each run stores, when it completes: rules passed, failed, didn't come up, critical
  findings, and calls stopped with an error. Stored, not
  recomputed on every read, so the runs list stays one query.
- **Who ran it:** the person (`created_by`, already stored) and the assistant's name
  from the connection, plus the session's name when the assistant gives one (new
  optional `session_name` on `run_scenarios`, as on `get_next_task`). Shown "Alex's
  Claude Code · Onboarding". Migration: `run.assistant_name`, `run.session_name` and the
  totals columns. Older runs show the person only.

### The Tests tab (design item 32)

- **Four tiles:** the verdict ("Version 88 · Verified", with "Full run · 19 Nov, 9:40" or
  "Version 88 was verified 19 Nov" or "No full run yet"), Coverage ("86%", "114 of 132
  rules have a scenario"), Checked ("41 of 43", "rules judged in the full run", or "—"),
  Scenarios ("38", "3 sets"). No Flaky or Warnings tiles.
- **Runs:** one row per run of the live version, newest first, five
  shown and "Show all N runs". Columns: When, Run ("Full · 7 × 3", "Set smoke · 7 × 3",
  "Pick · 2 × 3"), Result, Passed, Failed, Didn't come up, Critical, Version, Who.
  - A full run's Result is the verdict word in its colour; an on-demand run's is a muted
    Passed or Failed with "on demand".
  - Calls stopped with an error: a muted "3 calls stopped" under the result.
  - A run in progress: "Running · 12 of 21 calls" with a thin bar; the tab polls every
    5 seconds while one is.
  - Earlier versions' runs behind "N runs on earlier versions", grouped by version.
  - No drill-in.
- **Removed:** "Why it failed", "All rules", the Flaky and Warnings tiles, and the API
  fields that fed them (`failing`, `failing_checks`, `all_rules`).
- **Unchanged:** the empty states for no spec and no scenarios, and the Scenarios and
  sets section.
- **The tab label** keeps "Tests 86%", now coverage as tests written.
- **Phone width:** the compact rows of the design (state 8).

### The Spec tab

- Each rule shows its result from the current version's latest full run: Passed, Failed,
  Flaky, Didn't come up, or "No scenario". A category that has a failed rule shows "2
  failed" in its header.
- Under the spec's title: "Results from the full run of 19 Nov" or "No full run on
  version 88 yet". Without a full run, no marks.
- `GET /agents/{id}/spec` returns the marks and that line.

### `GET /agents/{id}/tests`

- Returns the tiles, the current version's runs newest first (paginated, with
  `next_cursor`) and the earlier versions' runs grouped, each run with its totals,
  verdict or on-demand result, and who ran it.

### MCP

- `get_test_runs` without `run_id`: the version's verdict with the run that decided it,
  `coverage` as tests written (rules with a scenario, and the rules without one),
  `checked` as rules judged in that run, and the runs with their totals and who ran
  them. Next steps by verdict: Partially tested names the rules that didn't come up and
  says to write or rewrite scenarios that reach them; Not verified says to run `all`.
- `run_scenarios`: next steps say a run of `all` is a full run that can verify the
  version, and a set or a pick is on demand and never changes the verdict.
- Every "rule" that means a code check reads "Found by a code check" in answers, guides
  and the call screen's line for a simulated call.
- `docs-internal/testing.md` decisions and the scenarios guide follow.

## Done when

- Route tests through the API (local database), with Retell and the model mocked:
  - a set run never changes the verdict; a full run with a critical failure is Failed,
    one with a rule that didn't come up is Partially tested, one with every rule checked
    and nothing critical is Verified;
  - a newer version without a full run is Not verified and names the last verified one;
  - `GET /agents/{id}/tests` returns the tiles, the runs with totals and who ran them,
    earlier versions grouped, paginated;
  - `GET /agents/{id}/spec` returns each rule's mark from the latest full run;
  - `get_test_runs` and `run_scenarios` answer as above, and the contract test passes
    with `session_name` described.
- For Dmytro to check on screen: the eight design states that real data can reach
  (Verified, Failed with the Spec tab, Partially tested, Not verified, a run in
  progress, earlier versions, light theme, phone width).

## Out of scope

- The version filter, the Version column on Calls, and "Spec 5 · written for version 88"
  (10.197).
- Drilling into a run's simulated calls from the Tests tab.
- Gate issues and failed-version Work tasks (Milestone 7).
- Rewriting the two production runs already stored: they were runs of a set, so they
  never counted toward the verdict under the new rules anyway.

## Risks

- Stored totals must be written when a run completes and when a restart fails it;
  a run that misses that shows empty counts. A backfill computes them for runs already
  stored.
- Removing `failing`, `failing_checks` and `all_rules` breaks nothing else: only the
  Tests tab reads them (checked with a search while building).

## Outcome

### Deviations from the plan

- **Run totals are computed when read, not stored.** Each run's rules (passed, failed,
  didn't come up, no scenario, critical, stopped) are worked out from its verdicts and
  calls when the runs are listed. This needs no backfill, and a restart that fails a
  run cannot leave empty counts. The migration (`0037`) only adds `run.assistant_name`
  and `run.session_name`.
- **Which rules a run's scenarios listed** comes from the judge's answers, which cover
  every listed rule, Didn't come up included. A scenario edited later therefore never
  rewrites a past run. The current lists only fill in rules for calls that stopped
  before a judge.
- **A run started without a version** belongs to the live version until it pins a
  number, so a full run in progress shows in the live version's table.
- **No pagination on the Tests tab.** It returns every run of the live version and at
  most 50 runs of earlier versions. `get_test_runs` keeps its paged list of runs.
- **Polling** uses TanStack Query with the server's copy as its first answer. It
  refetches every 5 seconds while a run is in progress and the tab is visible.
- **The Spec tab marks only the latest spec version.** An older version's rule keys may
  mean other words.
- **`edited` leaves the version's results.** The verdict reads the latest full run
  whatever an earlier draft did. A simulated call on the call screen still says it
  tested an edited draft.
- **The call screen's finding source** reads "Found by a code check" (was "Found by
  code").
- **Not done from the plan:** the plan had `GET /agents/{id}/tests` paginated with
  `next_cursor`; see "No pagination" above.

### Check results

`make check`, run before the pull request: every step ok (plan, local database, backend
lint and format, pyright, backend tests and coverage, MCP server tests, frontend lint and
types, generated client fresh).

No separate play-through server: the route tests send the same requests through the API
(`TestClient` on the local database), with Retell and the model mocked:
- a set that fails a critical rule leaves the version Not verified. A full run with
  both rules passed verifies it, with its totals and who ran it. A non-critical failure
  still verifies; a critical failure fails it;
- a full run whose scenario lists one of two rules is Partially tested, naming the
  other rule as having no scenario;
- a critical code check fails the full run and counts once as critical;
- a new live version without a full run is Not verified and names the last verified
  version; the earlier version's runs move under "earlier";
- a full run in progress shows as running in the live version's table;
- `GET /agents/{id}/spec` marks each rule from the latest full run and says when it ran;
- `run_scenarios` stores the session's name and says whether a run is full or on demand;
- the MCP adapter reads the new results and sends `session`.

For Dmytro to check on screen (agent page):
- **Tests tab:** four tiles (verdict with its subline, Coverage "N of M rules have a
  scenario", Checked, Scenarios) and the Runs table. Each row shows When, Run, Result
  (the verdict in its colour for a full run, a muted Passed or Failed with "on demand"
  otherwise), the counts, Version and Who.
- **While a run is in progress:** "Running · N of M calls" with a bar, filling in
  without a reload.
- **After a new version goes live:** "Version N · Not verified" with "Version M was
  verified …", and "N runs on earlier versions" opening the older rows.
- **Spec tab:** Passed, Failed, Flaky, Didn't come up or No scenario on each rule, "N
  failed" on a category, and "Results from the full run of …" under the title.
- **Phone width:** compact run rows with the counts on a second line.
- **Light theme:** the verdict colours.

### Not done

- No test for an older spec version showing no marks, and none for a scenario edited
  after a run. Both behaviours are written but not exercised by a test.
