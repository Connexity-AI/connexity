# Test results

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Test results" (10.1293). It comes after
  the text runner (10.1292, #221) and before the Tests tab (10.1294).
- **Design:**
  - `docs-internal/testing.md`, which wins over `designs/08-testing.md`;
  - `designs/09-calls.md`, the line for a simulated call. It shows one rule
    ("Proves: … · Failed"), but a scenario lists several (question 6).
- **MCP:**
  - `get_test_runs` gains a version's results: its verdict and the totals per rule
    across its runs;
  - each simulated call gets a link the assistant can show the person.

## Goal

After the assistant runs scenarios, everyone can see whether the version they tested
holds up:
- **The rules:** per rule, across every run of the version, "R31: 14 passed, 1 failed,
  3 didn't come up".
- **The verdict:** Failed or Verified, with its warnings.
- **The simulated calls:** each one opens like any call, with a line naming the rules it
  was judged on and their verdicts.

The assistant reads the same through MCP, with next steps.

## Decided

These are Dmytro's words, in `testing.md`:
- **What counts is the total of rule verdicts passed and failed** (decision 5).
- **A failed critical rule fails the version; a failed non-critical rule is a Warning,
  with a threshold** (decision 6).
- **Code checks run on simulated calls, and a regression they find is flagged**
  (decision 10).
- **The gate runs every scenario** (decision 12).
- **Failures found by the gate are issues; issue analytics count production only**
  (decisions 14 and 15).

From the roadmap row:
- **"Didn't come up" is not counted.**
- **A flaky critical rule counts as failed.**
- **One fixed default threshold for now.**

## What exists

- **A run records what it tested:**
  - the Retell version number;
  - "the latest" pinned to a number;
  - each simulated call (`test_case_result`), with its code-check findings and a
    `rule_verdict` per listed rule.
- **`get_test_runs` totals one run's rules.** Nothing totals a version yet.
- **A draft keeps its version number while it is edited.** On Retell, an unpublished
  version is edited in place. So runs before and after a prompt fix can share
  "version 15" and test different prompts.
- **Version content can be read and fingerprinted.** `component_versions` reads a
  version's agent settings, prompt or flow, and model from Retell, and fingerprints
  each. Its catalogue keeps the first content it saw for a version number, so it
  cannot tell a draft's edits apart.
- **The call screen** (`/calls/{id}`) reads `call` rows only. Findings are critical
  when their check fails calls, and warnings when it flags them.

## Changes

### What "a version" is (question 1)

- **When a run starts,** it reads the version it tests from Retell (agent settings,
  prompt or flow, model). It stores one fingerprint of that content on the run
  (`run.version_fingerprint`).
- **Results are grouped by version number and fingerprint.** When the draft was edited
  between runs, the edited one is a new group: "Version 15, edited 14:02". Runs of the
  earlier content no longer count for it.
- **When Retell cannot be read,** the run keeps only the number and is grouped with
  others like it.

### A version's results

- **Which runs count** (question 2): every completed run of the version. That means
  sets, picks and "all" alike.
- **Totals per rule:** passed, failed and didn't come up, summed across those runs'
  simulated calls. Flaky is a rule that both passed and failed.
- **Code checks:** each check that found something, with how many simulated calls it
  found it in and its severity:
  - Critical when the check fails calls;
  - Warning when it only flags them.
- **The verdict:**
  - **Failed** when a critical rule failed (flaky included), when a critical code check
    found something, or when warnings go over the threshold;
  - **Verified** otherwise, with the number of warnings;
  - **Not tested** when no run of the version completed.
- **Warnings:** each non-critical rule that failed at least once, and each code check
  with only Warning findings.
- **The threshold** (question 3): the version fails when more than 20% of the
  non-critical rules judged (passed or failed at least once) failed. It is one fixed
  default, `testing.md` open question 1.
- **What the verdict does not cover:** how many rules were tested at all. That is
  coverage, on the Tests tab (10.1294).

### A simulated call on screen (question 6)

- **`/calls/{id}` opens a simulated call** too, by the simulated call's id. It shows:
  - **the page bar** with a "Simulated" label and the version;
  - **one line** with the rules it was judged on and their verdicts, failed first.
    Each verdict opens its reason.
  - **findings and the transcript** as on any call, with tool calls inline;
  - **no player and no times:** there is no recording, and a text run has no timing.
- **Its result label** (question 7):
  - Failed when a critical rule failed or a critical finding was raised;
  - Degraded when only non-critical rules failed or only warnings were raised;
  - Clean otherwise.
- **How the person gets there:** the assistant gives the link from `get_test_runs`. The
  calls list's "Simulated" source and the Tests tab come later (10.1294). Nothing
  else on screen links to it yet.

### MCP (question 5)

- **`get_test_runs(…, version?)`:** without `run_id`, it answers the results of the
  version (by default the newest one tested):
  - its verdict, the totals per rule (failed and critical first) and the code checks;
  - the warnings and the threshold;
  - the runs that count.

  The runs list stays, paged as now.
- **Each simulated call in a run's detail** gains `url`, the link to it in the app.
- **Next steps:**
  - **Failed:** name the failed critical rules and their calls' links. Then: read the
    reasons, fix the scenario if it is wrong, otherwise tell the person what failed
    and what you suggest.
  - **Verified with warnings:** name them.
  - **Edited since the last run:** "The draft changed since these runs; run the
    scenarios again."
- **`run_scenarios`' answer** points at the version's results once the run is done.

## Decisions

- Everything under "Decided" is Decided.
- **Questions 1 to 7 are Decided as recommended** (Dmytro, "Accept, build",
  2026-11-17).

## Questions

1. **A version is its number and its content.** Recommend storing a fingerprint of the
   tested content on each run and grouping results by number and fingerprint, so a
   draft edited after a failing run starts fresh. The alternative is the number only,
   simpler, but a fixed draft keeps its old failures until it is published as a new
   number.
2. **Which runs count.** Recommend every completed run of the version: sets, picks and
   all. A failure in a pick is still a failure of that version. The alternative is
   only runs of every scenario (the gate's runs), so the verdict always rests on the
   full set, and a version with only a pick run shows Not tested.
3. **The default threshold.** Recommend: the version fails when more than 20% of the
   non-critical rules judged failed at least once. The alternative is a fixed count,
   such as more than 3 failed non-critical rules. That is easier to say, but it does
   not grow with the spec.
4. **No issues and no Work task here.** Gate issues (decision 14) and a "Version failed"
   task for the assistant (`testing.md`, Proposed) need the gate, which is Milestone 7.
   Recommend leaving both out. The alternative is the Work task now: "Version 15 of
   Front desk failed 2 critical rules".
5. **Extend `get_test_runs` rather than add a tool** (rule 10). Recommend extending it:
   without `run_id` it answers the version's results and its runs. The alternative is a
   new `get_test_results` tool, clearer by name, but a near-duplicate of the runs list.
6. **The simulated call's line needs a design adjustment** (rule 9). The design shows
   one rule ("Proves: … · Failed"). Recommend writing a Claude Design prompt in
   `designs/12-adjustments.md` (item 30):
   - the rules judged with their verdicts;
   - no player and no times for a text run;
   - the "Simulated" label.

   The backend and MCP are built first, and the screen follows your design update in
   the same PR, as with Critical rules. The alternative is backend and MCP only here,
   and the screen with the Tests tab.
7. **A simulated call's result label** comes from its verdicts and findings, as above.
   Recommend this, so a call that failed a critical rule never reads Clean. The
   alternative is findings only, as on real calls.

## Done when

- **Through the API,** in route tests on the local database, with Retell and the model
  mocked:
  - a run stores the tested content's fingerprint, and an edited draft starts a new
    group;
  - a version's totals add up across its runs;
  - each verdict:
    - Failed by a critical rule, by a flaky critical rule, by a critical code check
      and by the threshold;
    - Verified with warnings;
    - Not tested;
  - `get_test_runs` answers the results with next steps and a link per simulated
    call;
  - the call screen answers a simulated call in the workspace, with its judged rules
    and result label, and 404 for another workspace's.
- **`make check` passes** once, before the pull request.
- **For Dmytro on screen** (after the design update): a simulated call opened from the
  assistant's link, in dark and light.

## Out of scope

- Gate issues, the failed-version Work task and overriding a failed version (the gate,
  Milestone 7), if question 4 goes as recommended.
- The Tests tab, coverage and the calls list's "Simulated" source (10.1294).
- Gate settings and per-agent thresholds (Milestone 7).

## Risks

- **Reading Retell at each run start** adds a few requests. If Retell is down, the run
  still runs and is grouped by number only.
- **The 20% threshold is a guess** until real runs show how often non-critical rules
  fail. It is one constant, easy to change.

## Outcome

### Deviations from the plan

- **Built on the text runner's branch** (#221, merged since).
- **A run reads its content even when the version was given,** and after "the latest"
  is pinned. If the read fails for any reason, the run still runs, grouped by number
  only.
- **"Edited" is worked out per run:** a run is edited when an earlier run of the same
  number read different content. A run whose content could not be read says nothing
  either way. The call screen uses the same rule.
- **The "edited since the last run" next step** reads "The draft was edited under the
  same version number since earlier runs; only runs of the current content count", on
  both a failed and a verified version. Connexity does not read Retell on every
  `get_test_runs` to see whether the draft changed since the newest run.
- **The reason a conversation stopped** is in plain words ("The conversation stopped:
  Retell returned no messages"), without the platform's raw marker. A judge failure
  shows the judge's own message in the same place.
- **The call screen's simulated call follows design item 30,** updated in
  `designs/screens/Connexity Call.dc.html`:
  - the page bar shows the time, "Version 15" and "Edited", with a "Simulated" label;
  - "Scenario: …" with a chip per rule (Critical badge on a failed critical rule),
    failed first, and "Not judged" when it stopped;
  - a chip opens the judge's reason and the turns, which scroll to the turn;
  - no player; turn numbers instead of times; findings at "Turn N";
  - the stopped line ends the transcript.
- **Review findings:**
  - fixed: unread content no longer marks a version edited; the edited note shows on
    a failed version too; any failed content read no longer stops a run;
  - skipped: results read whole simulated calls, transcripts included, to count.
    Fine at demo scale.

### Check results

`make check`:

| Gate | Result |
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

While building, only the touched test files ran:
- `test_test_results.py` (new), `test_test_runs.py`, `test_call_screen.py`,
  `test_runs.py`, `test_scenarios.py`, `test_spec_api.py`, `app/tests/crud` and
  `app/tests/services`;
- the MCP server tests.

No separate play-through server: the route tests send the same requests through the API
on the local database, with Retell's playground, its version reads and the model mocked.
- **Content and versions:**
  - two runs of the same content share a fingerprint;
  - an edited prompt under version 15 starts new results, marked edited.
- **A version's results** add up its runs: one passed and one failed make the critical
  rule flaky and the version Failed. A version you name answers the same, and an
  unknown version is a 404.
- **A critical code check** fails the version and its simulated call.
- **A version without a completed run** is Not tested.
- **The verdict's rules** are tested directly:
  - 1 of 5 non-critical failures is a warning;
  - 2 of 5 is over 20% and fails;
  - a rule that never came up is not counted;
  - a flaky critical rule fails;
  - a flag-only check is a warning.
- **The call screen** answers a simulated call:
  - its verdicts, the entries they point to, and Edited;
  - no recording and no caller;
  - "no result" for a default fake;
  - its result from verdicts and findings;
  - a stopped conversation as Unchecked with the reason;
  - another workspace's call is a 404.
- **`get_test_runs`** gives each simulated call its link.

`test_test_runs.py`'s check totals gained `critical`; nothing was weakened.

After the screen, `eslint`, `tsc` and `pnpm --filter connexity build` pass on the
frontend.

**For Dmytro to check on screen.** Open a simulated call from the link
`get_test_runs` gives, after a run against a test agent:
1. **The page bar:** the time, "Version N" and, after an edit, "Edited", with Failed,
   Degraded or Clean and a "Simulated" label. No duration and no caller.
2. **Under it:** "Scenario: …" and a chip per rule, failed first, the Critical badge
   only on a failed critical rule.
3. **A chip opens the judge's reason** with turn buttons. A turn button scrolls to and
   highlights that turn.
4. **No player.** Findings show "Turn N" and jump to their turn. The transcript shows
   turn numbers, and tool lines have no duration.
5. **A conversation that stopped** reads "Not judged" on the line and ends with "The
   conversation stopped: …".
6. **Dark and light.**

### Not done

- Gate issues, the failed-version Work task and overriding a failed version (the gate,
  Milestone 7).
- The Tests tab, coverage and the calls list's "Simulated" source (10.1294).
- A real run against a Retell agent, as for the runner.
