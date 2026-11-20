# Test runs the assistant can trust

- **Owner:** Dmytro
- **Slice:** "Fix: test runs the assistant can trust" (roadmap, Test stage), first of two pull
  requests: what a result proves. Progress and speed (items 4 and 6) follow in the
  second, drafted in `plans/drafts/2026-11-20-test-run-progress-and-speed.md`.
- **Design:** No UI change. The Tests tab keeps its layout; some of its numbers change
  because verdicts that are not evidence stop counting (see Changes, 2 and 3).
- **MCP:** `get_test_runs` is extended (no new tool, no new input): new facts on every
  run, simulated call and verdict. `run_scenarios` gains one rule line. The
  contract page entries, input descriptions, tool rules and the scenarios guide follow.

Status: **approved by Dmytro on 2026-11-20 ("Accept, build")**. Statements are marked Decided (Dmytro's
words, from the roadmap row or his answers on 2026-11-20), Proposed (Claude) or Open.

## Goal

An assistant maintaining a client agent through Connexity could not rely on a run's
result. After this merges, a run says by itself everything that limits what it proves:
whether the version changed since, which verdicts rest on a made-up tool answer, which
spec it judged against, and that tool schemas were not applied. The judge also stops
contradicting its own reasons.

## Changes

Numbered as in the roadmap row; 4 and 6 are the second pull request.

**1. Every run says whether its version changed since**
- Today only the version's results (`edited_since`, `same_content`) say it, and only
  relative to a full run, so a smoke run got nothing.
- Every run, in the list and by `run_id`, carries `content`: `same`, `edited` or
  `unknown`, with `content_checked_at`. `edited` means the version number now holds
  different content than this run tested.
- "Now" is a read of the version on Retell when `get_test_runs` is asked for one run or
  for a version's results (Decided, Dmytro 2026-11-20). Without it, an edit made after the
  last run is invisible until the next run. When Retell cannot be read, `unknown`, never
  `same`.

**2. The judge reasons first, then gives its verdict**
- The verdict is already a separate structured field. The judge writes it before the
  reason, so it commits and then reasons its way to the opposite conclusion.
- The judge writes the reason first, then the verdict (field order in the answer).
- Nothing reads the reasons a second time: no extra model call (Decided, Dmytro
  2026-11-20, who rejected it). A contradiction that still happens is not caught; see
  Out of scope.

**3. Verdicts that depended on a default fake are marked**
- A verdict is marked `default_fake` with the tools' names when a tool with no fake in
  the scenario answered before or at the turns the verdict rests on.
- A marked verdict does not count: its rule is "not checked", with why, as a call that
  stopped is today (Decided, Dmytro 2026-11-20). So a full run with default fakes can end
  Partially tested instead of Verified or Failed, and the next step names the tools to
  fake.

**5. The run says tool schemas were not applied**
- Every run carries `tool_schemas_applied: false` and one rule line: a simulated call
  fakes every tool, so the platform's tool schema (required fields, patterns) is not
  applied, and a green run does not prove a schema fix.

**7. A run says which spec it judged against**
- A run already stores its spec. Every run shows `spec_version` and the agent version
  that spec was written for, and `spec_behind: true` with a next step when the tested
  agent version is newer than that: "the spec was written for version 87; this run
  tested 89 against it. Update the spec, or confirm nothing in it changed."
- It warns and never refuses the run (Decided, Dmytro 2026-11-20: "ok agree though i
  dont like it").

**Data**
- One migration: `rule_verdict` gains `mark` and `mark_detail`. Nothing is
  backfilled: earlier runs read as unmarked.

**Docs**
- `docs-internal/testing.md`, the scenarios guide, `/mcp-docs` entries.

## Decisions

| # | Decision | By |
|---|---|---|
| 1 | Items 1 to 7 and "MCP: get_test_runs answers all of the above" | Decided (Dmytro, roadmap row, 2026-11-20) |
| 2 | A Cloud Run setting is reported, not changed here | Decided (Dmytro, roadmap row) |
| 3 | Two pull requests: results first (1, 2, 3, 5, 7), then progress and speed (4, 6) | Decided (Dmytro, 2026-11-20, chose "Two PRs") |
| 4 | "Now" for item 1 is read from Retell when asked | Decided (Dmytro, 2026-11-20, chose "Read Retell when asked") |
| 5 | Verdicts marked as resting on a default fake count in no column | Decided (Dmytro, 2026-11-20, chose "Do not count") |
| 6 | No second model call reads the judge's reasons; the fix is the order, reason then verdict | Decided (Dmytro, 2026-11-20, rejected the second read) |
| 7 | `spec_behind` warns, never refuses | Decided (Dmytro, 2026-11-20: "ok agree though i dont like it") |
| 8 | No Tests tab design change; the new facts reach people through the assistant | Decided (Dmytro, 2026-11-20: "agree") |

## Done when

- A set run of a version, then an edit of that version on Retell: `get_test_runs` with
  the run's id says `content: edited`. With Retell unreachable it says `unknown`.
- The judge's answer carries each rule's reason before its verdict, and the judge's
  tests pass with that order.
- A scenario that leaves a tool without a fake: verdicts resting on turns after that
  tool's answer are marked with the tool's name, and their rules are "not checked".
- Every run answer has `tool_schemas_applied: false`, `spec_version`, and `spec_behind`
  when the tested version is newer than the spec's.
- The contract tests pass with the new field descriptions; `make check` passes.

## Out of scope

- **For Dmytro: Cloud Run CPU.** If `connexity-backend` gives CPU only during requests
  (the default), a run slows whenever nothing is polling it. Setting CPU to always
  allocated (`--no-cpu-throttling`) and one minimum instance is the likely fix. Not
  changed in this pull request.
- Applying the agent's real tool schemas: the next roadmap row.
- Progress, stalls, cheap polling, the time split and more calls at once: the second
  pull request.
- The gate and "Verify a candidate version".
- Any change to the Tests tab's design.
- Catching a verdict that still contradicts its reason. The roadmap row asks for it;
  Dmytro rejected the second model call that would do it. Whether the new order is
  enough is read from the next production runs.

## Risks

- Item 3 can turn versions that read Verified today into Partially tested, when their
  scenarios leave tools unfaked. That is the intent, but it will be visible.
- Reason-first should remove most contradictions but is not proof; one that remains is
  still stored as a failure.
- Reading Retell on `get_test_runs` makes that read depend on Retell; it falls back to
  `unknown`.

## Outcome

### Deviations from the plan

- **Edited since, in the list of runs.** Retell is read for one version per request:
  the run asked for, or the version whose results are asked for. Runs of other version
  numbers in the same answer are not read. They say `edited` when a later run of the
  same number saw other content (proof without a read), otherwise `unknown`.
- **No read while a run is in progress.** A pending or running run answers `unknown`
  without asking Retell, so a poll never waits on the platform. Found in code review.
- **`content_checked_at`** is set only when Retell was read for that run's version.
- **An on-demand run whose every verdict is marked has no result** (`result` is empty),
  not `passed`. The plan did not say; found in code review.
- **A simulated call's result ignores marked verdicts too** (the call screen's label),
  so a call does not read Failed for a verdict that is not counted. The plan named only
  runs and versions.
- **The spec warning compares with the agent version the spec's rules were written
  for** (`written_for`), not the version that last adopted the spec, since adopting a
  spec for a new version does not review its rules. The answer names it as
  `spec_written_for`.
- **`mark_detail` is a list** of tool names.
- `plans/drafts/2026-11-20-test-run-progress-and-speed.md` is added: the draft for the
  second pull request.

### Check results

`make check`, run once on the final code:

| Step | Result |
|---|---|
| Plan present and complete | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

Route tests send the requests through the API on the local test database
(`TestClient`); no separate play-through server was used.

| Request | Expected | Came back |
|---|---|---|
| Full run, judge fails a critical rule on a turn after an unfaked tool answered; `GET test-runs?run_id=` | verdict `mark` `default_fake` with the tool; rule failed 0, `default_fake` 1; nothing critical; next step names the tool | as expected |
| Same, as a pick | `result` empty, not `passed` | as expected |
| Pick run of version 15, then `GET test-runs?run_id=` with Retell holding the same prompt | `content` `same`, `content_checked_at` set | as expected |
| Same, Retell holding an edited prompt | `content` `edited`; first next step says the version was edited after this run | as expected |
| Same, Retell answering 500, timing out, not JSON, or a list | `content` `unknown`, never `same` | as expected |
| Full run verified, then `GET test-runs` with Retell holding an edited prompt and no new run | `not_verified`, `edited_since` set, the run `edited` | as expected |
| Run of version 15 on a spec written for 7; run of version 7 | `spec_behind` true with a next step; false without one | as expected |
| Any run | `tool_schemas_applied` false, and a rule line saying so | as expected |
| The judge's answer format | reason, turns, then outcome, in that order; an answer in that order is read | as expected |

Existing tests changed, said here because they pin behaviour: their invented judge
answers now cite turn 1 instead of turn 4, since turn 4 comes after a default fake and
would be marked; one call-screen assertion follows (entry 1, not 3). Three files:
`test_test_runs.py`, `test_test_results.py`, `test_tests_tab.py`. No test was
removed or loosened.

### Not done

- **Catching a contradiction that still happens** (see Out of scope).
- **The call screen and the Tests tab do not show the mark.** A marked verdict still
  reads Failed or Passed in a simulated call's rule list, while the call's result and
  the run's numbers no longer count it. Showing it needs a design change first.
- **Not verified on production.** Whether reason-first removes the contradictions, and
  how many verdicts get marked on real scenarios, is seen on the first runs after
  merge.
- **Runs made before this change** carry no marks; their numbers do not change.
