# Verified only when a rule was checked

- **Owner:** Dmytro
- **Slice:** none (a bug fix in the Tests tab, roadmap 10.15x results)
- **Design:** No UI change. The Verdict tile's "Not tested" state gains a short note.
- **MCP:** No tool changes. `get_test_runs` answers `not_tested` in this case, with a
  next step saying the runs checked no rule.

## Goal

Dmytro, 2026-11-19, with a screenshot of the Tests tab showing "Version latest ·
Verified" at 0% coverage and 0 of 0 rules checked: "whenever test runs start it
updates this UI and make claim its verified but its a false".

The cause: a version counted as tested once any run of it completed, even when every
simulated call failed before a judge read it (here, all 21 calls on the missing
Anthropic key). Nothing failed, so it read Verified.

## Changes

- **The verdict needs a checked rule.** A version with completed runs but no rule judged
  passed or failed is Not tested. A critical rule or a critical code check still fails
  it whatever else happened.
- **`get_test_runs`** says the runs completed but checked no rule, and points to the
  run's calls for the error.
- **The Tests tab:**
  - the Not tested tile adds "its runs checked no rule" when runs exist;
  - "Verified" shows only for a `verified` verdict.

## Decisions

- **Decided (Dmytro, 2026-11-19):** a version that was not checked is never shown as
  verified.

## Done when

- A completed run whose calls all failed leaves the version `not_tested`, through the
  API in a test, with the new next step.
- `_verdict_of` with no rule judged is `not_tested`; with a critical check it is
  `failed`.

## Out of scope

- "Version latest" on a run that never pinned its version number.
- How many judged rules make a verdict meaningful: one is enough, as before.

## Risks

- None known: only versions that checked nothing change.

## Outcome

### Deviations from the plan

None.

### Check results

`make check`: every step ok. Route tests ran through the API on the local
database (`TestClient`).

**Tests:**

- `test_test_runs.py`: a run whose only call stopped on a platform failure completes,
  and the version is `not_tested`, with "checked no rule" as the first next step.
- `test_test_results.py`: `_verdict_of` with two rules never judged is `not_tested`, and
  with one critical code check it is `failed`.
- `test_test_results.py`, `test_test_runs.py` and `test_tests_tab.py`: 26 pass.

### For Dmytro on screen

The agent's Tests tab, after a run whose calls all failed: Verdict reads "Not tested",
with the version and "its runs checked no rule".

### Not done

None.
