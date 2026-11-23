# Verify a candidate version, and confirm a fix on real calls

- **Owner:** Dmytro
- **Slice:** "Verify a candidate version" (roadmap, Gate stage)
- **Design:** No screen is built. The issue page's design prompt
  (`designs/10-issues.md`) gains the "since version N went live" line, for Dmytro to
  paste into Claude Design (decision 4).
- **MCP:** no new tool. `get_issue` gains what happened since a version went live
  (one new answer block, one new optional input). `get_test_runs` says plainly what a
  verdict means for publishing. Contract page entries and input descriptions updated.

Status: **approved by Dmytro, 2026-11-21 ("Accept, build")**. Statements are marked Decided
(Dmytro, from the roadmap row or `docs-internal/testing.md`), Proposed (Claude) or
Open.

## What was found before planning

The row has two halves. The first is already built.

**Half one: verify a candidate before it ships.** Works today, with existing tools:
- `run_scenarios` with `all` runs every scenario on a version the assistant names, or
  on the agent's newest version on Retell, which is the draft being edited.
- `get_test_runs` answers that version's verdict (Verified, Failed, Partially tested,
  Not verified) with the failing critical rules, warnings and next steps.
- The row's open question, "can tests run against an unpublished draft version", is
  answered: yes. On the hosted database (read only, counts only, 2026-11-21) all 3
  runs of scenarios tested a version that had never served a real call.

**Half two: confirm the fix on real calls.** Not answerable today:
- An issue marked fixed in a version knows when that version went live (its first
  real call on that version or a later one), and reopens if it is found again after.
- But nothing says how many calls there have been since. "Resolved, not reopened"
  reads the same after 2 calls as after 200. The 30-day counts still include every
  call from before the fix.
- Hosted data today: 104 real calls on 1 agent version, 4 open issues, none marked
  fixed yet. So this cannot be tried on real data until a fix ships.

## Goal

After shipping a fix, the assistant asks one question, "has this issue stopped since
version N went live?", and gets numbers: calls since, calls with this issue since. A
fix is then confirmed, or rolled back, on evidence. Before shipping, the verdict
answer says in plain words whether the version passed the gate.

## Changes

**Since a version went live (`get_issue`)**
- For an issue marked fixed in a version, or reopened after one, the answer carries
  `since_fix`: the version, when it went live, the agent's real calls from then on
  that ran that version or a later one, how many of them have this issue, and the
  last of those.
- Counting follows the rule that already reopens issues: a call counts when its
  version is the fix's version or a higher number (Decided, built in mark fixed and
  reopen). A call still served by an older version after the fix went live is not
  counted.
- The first next step says it in one sentence: "Since version 16 went live (19 Nov):
  42 calls, 0 with this issue." With no call yet: "Version 16 has not served a real
  call yet."
- A new optional input, `since_version` (Decided, Dmytro 2026-11-21): the same
  numbers for any version, for an issue that was never marked fixed.
- No verdict from Connexity such as "confirmed": it gives the numbers and their
  base; the assistant and the person judge (Proposed, decision 5).

**The verdict before shipping (`get_test_runs`)**
- When a version is Verified and is not the live one, the steps say it passed the
  gate and can be published; when Failed, that publishing it is an override a person
  decides (the override itself is the roadmap row after this one).
- Nothing else changes in running or judging.

**Design prompt**
- `designs/10-issues.md` gains the line the issue page shows for a fixed or reopened
  issue: "Since version 16 went live, 19 Nov: 42 calls, 0 with this issue", with its
  empty state. Text only; Dmytro pastes it into Claude Design.

**Docs**
- `docs-internal/testing.md` (the open question closed, the release loop's two
  halves), `docs-internal/checks-and-incidents.md` (what "since the fix" counts), the
  issues guide and scenarios guide served over MCP, the `/mcp-docs` entries.

## Decisions

| # | Decision | By |
|---|---|---|
| 1 | The gate runs every scenario; a version's verdict comes from its latest completed full run | Decided (Dmytro, 2026-11-17 and 2026-11-19) |
| 2 | No new "verify" tool: `run_scenarios` with `all`, then `get_test_runs`, is the verify ask. CLAUDE.md rule 10: extend a tool before adding a near-duplicate | Proposed |
| 3 | `get_issue` takes an optional `since_version`, so the question also works for an issue never marked fixed | Decided (Dmytro, 2026-11-21, chose "Yes, any version") |
| 4 | No screen is built here. This pull request writes the issue page's design prompt text for the line; the screen is built later, after the design has it | Decided (Dmytro, 2026-11-21, chose "Write the design prompt too") |
| 5 | Connexity gives the counts and never calls a fix "confirmed" on its own | Proposed |
| 6 | A call counts as "since the fix" when it ran the fix's version or a later one | Decided (already how an issue reopens) |

## Done when

- An issue marked fixed in version 16, then 3 real calls on version 16 without it:
  `get_issue` says since version 16 went live, 3 calls, 0 with this issue.
- A fourth call on version 16 with the issue: the issue reopens and `get_issue` says
  4 calls, 1 with this issue.
- A call on version 15 after version 16 went live is not counted.
- An issue marked fixed in a version with no real call yet says so.
- A Verified version that is not live: `get_test_runs` says it passed and can be
  published. A Failed one says publishing it is a person's override.
- Another workspace cannot read any of it; the contract tests and `make check` pass.

## Out of scope

- Overriding a failed gate (its own roadmap row).
- The pre-deploy hook and standing instructions (its own roadmap row).
- Issues created from gate failures (`docs-internal/testing.md`, open questions 6
  and 7).
- Building the issue page's line (after the design has it; needs its own roadmap
  row).

## Risks

- With few calls since a fix, "0 with this issue" proves little. The answer always
  gives the base, and a rule tells the assistant to say how many calls it rests on.
- Version order is known only where versions are numbers (Retell). Elsewhere only the
  exact version counts, as for reopening today.

## Outcome

Built as planned, with the deviations below. No screen, no migration, no new tool.

- `get_issue` answers `since_version`: the version, whether it is the issue's fix,
  when it went live, the agent's real calls on it or a later version, how many have
  the issue, and the newest of those. The first next step says it in a sentence. The
  optional `since_version` input asks the same for any version.
- `get_test_runs`: a Verified version ahead of the live one is said to have passed
  the gate and can be published; a Failed one, that publishing it is an override only
  a person decides.
- `designs/10-issues.md` has the text of the line for the issue page.
- Guides (issues, scenarios), the `/mcp-docs` entry and input description,
  `docs-internal/testing.md`, `checks-and-incidents.md`, `mcp-architecture.md`.

### Deviations from the plan

- **The block is named `since_version`, not `since_fix`,** because it also answers
  for a version that is not the fix; `is_fix` says which it is.
- **A fix still waiting to go live adds no new sentence:** the existing step already
  says "waiting for version N to go live". The block is still in the answer.
- **The publish wording is given only for a version ahead of the live one** (a higher
  number, or no real call yet). An older version that was tested is not called
  publishable, and where versions are not numbers nothing is said.
- **Decision 6 was not fully true (Open, for Dmytro).** An issue reopens by time: any
  call with the issue that started after the fix went live reopens it, also one an
  older version served. The counts go by version, as decided, so that call is not
  counted. When this happens the step says the issue was reopened by a call on an
  older version that is not counted. Whether such a call should reopen at all is not
  decided and nothing was changed there.
- **Two existing assertions moved, none weakened:** in `test_mark_fixed.py` the "and
  live" and "came back" steps are now the second step, after the new sentence.

### Check results

- `make check` (every gate, run once on 2026-11-21 on the finished branch): all
  passed, backend tests with coverage, MCP server tests, lint, types, client codegen
  freshness and the plan check included.
- Tested through the API with route tests on the local test database
  (`test_mark_fixed.py`, `test_test_results.py`); no separate play-through server,
  since those tests send the same requests the tools send.
- The "Done when" list: each line is an assertion in those two files, the other
  workspace's 404 included.

### Not done

- Not tried on real data: the hosted data has no issue marked fixed (counts only,
  read 2026-11-21).
- The line on the issue page is not built; it needs its own roadmap row after the
  design has it.
- Code review (5 findings): 3 fixed (the reopened-with-0 sentence, calls without a
  version documented, the year in the date); 1 left and documented (a deleted call
  counts for nothing here, while the fix's own live date is set from every call);
  1 needed no change (a blank `since_version` is treated as not given).
