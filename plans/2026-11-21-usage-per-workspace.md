# Usage per workspace

- **Owner:** Dmytro
- **Slice:** "Usage per workspace" (roadmap, Platform stage)
- **Design:** No UI change. The row says a usage screen comes with Billing, design
  first.
- **MCP:** one new tool, `get_usage` (a period's usage and list-price cost per
  workspace, agent and run, with what moved it most). `run_scenarios` and
  `get_test_runs` say what a run cost. Contract page entries and input descriptions
  for all three.

Status: **approved by Dmytro on 2026-11-21** ("Accept, build"). Statements are marked Decided
(Dmytro, from the roadmap row of 2026-11-20 or his answers on 2026-11-21), Proposed
(Claude) or Open.

## What was found before planning

Counts from the hosted database, read only, on 2026-11-21. One workspace, one agent.

| | Today |
|---|---|
| Real calls stored | 104, all with an end time, all by phone |
| Their minutes | 180 counted to the second; 235 if each call is rounded up to a minute |
| Calls marked as test calls | 0. Nothing marks one today: every call synced from Retell is stored as a real call |
| Simulated calls | 63, with 328 simulated caller messages; 8 of those are in a call that stopped with an error |
| Connexity's own model cost recorded | $0.06 on 49 of the 63 simulated calls; $0.02 on 104 model checks |

Three things follow:
- **Rounding matters:** rounding each call up to a minute bills 30% more minutes than
  counting seconds, on this data.
- **"A test call is never counted" has nothing to stand on yet.** The rule is decided,
  but no call is recognised as a test call.
- **The recorded model cost is small because the model is cheap.** $0.06 for 328
  caller messages and 63 judge calls is what the simulation model costs at $0.10 per
  million tokens in and $0.50 out, which is Anthropic's list price for it (checked
  2026-11-21; five times more above 100,000 tokens in one request, which no call
  here reaches). 14 simulated calls have no cost recorded.
- **Anthropic does not return dollars per request.** Each answer carries token
  counts only (in, out, cache read, cache write). Dollars exist only in Anthropic's
  cost report for the whole organisation, by model, workspace and API key, per hour
  or day, some hours behind. So cost per call is always tokens times a price list we
  keep, and the only proof it is right is comparing our total with that report.

## Goal

While working on agents, Dmytro and any workspace can see what the work costs at list
price: this period's observed minutes and simulated caller messages, per workspace,
per agent and per run, and what moved it most. Nothing is billed.

## Changes

**The meters**
- **Observed minutes:** each real call's length, rounded up to a whole minute per call
  (Decided, Dmytro 2026-11-21): a 95-second call is 2 minutes. A call without an end
  time counts nothing until it has one. Simulated calls are never counted (Decided).
- **Test calls:** nothing marks a call as a test call yet, so every call synced from
  the voice platform counts as a real call for now (Decided, Dmytro 2026-11-21, chose
  "Nothing yet"). The rule that a test call is never counted holds from the day test
  calls are recognised; a call stored with the test source is already left out.
- **Simulated caller messages:** each message the simulated caller sends in a text
  simulation, judge included in the price. Messages in a call that later stopped with
  an error count too (Decided, Dmytro 2026-11-21, chose "Count them"). The agent's replies are not counted: Retell
  bills them on the agency's own account (Decided).
- **Voice simulation minutes:** in the price list, recorded by nothing until voice
  simulations exist (Decided).

**Prices in one place**
- One price list in the backend: $0.03 per observed minute, $0.02 per simulated caller
  message, $0.25 per voice simulation minute (Decided). Dollars are always units times
  the list price at the time of reading; no discount, no plan, no balance.

**Recording**
- A `usage_record` table: workspace, agent, meter, quantity, when it happened, the
  call or simulated call it came from, the run for a simulated call, and Connexity's
  own model cost for it.
- A real call writes its record when it is stored, and replaces it when the call is
  read again (a late end time), so a call is never counted twice.
- A simulated call writes its record when it finishes.
- Usage before this change is filled in by the migration from the real calls and
  simulated calls already stored (Decided, Dmytro 2026-11-21).
- Recorded, not worked out on reading: usage must outlive a deleted call and a
  retention limit.

**Reading**
- `get_usage` answers a period (a calendar month, this month by default, or the last
  7 or 30 days): totals per meter in units and dollars, per agent, per run, and the
  three things that moved it most ("run of 'smoke' on 19 Nov: 189 messages, $3.78").
- `run_scenarios` says the price per caller message and what the last run of the same
  scenarios cost.
- `get_test_runs` shows each run's caller messages and list-price cost.
- Everything is scoped to a workspace the person can reach, like every other tool.

**Connexity's own cost**
- Each usage record carries the model cost Connexity paid for it (the simulated
  caller and the judge for a simulated call; model checks for a real call), where the
  model library reports one, with the token counts behind it by kind (in, out, cache
  read, cache write) and the model, so a cost can be worked out again if a price
  changes.
- The 14 simulated calls without a cost: find why while building, and record one
  where a model answered.
- It is stored and never returned by `get_usage` or any workspace route (Decided:
  not shown to customers). Dmytro reads the margin from the database (Decided,
  Dmytro 2026-11-21, chose "Database only").
- Comparing each day's recorded cost with Anthropic's own cost report is a second
  pull request under this roadmap row (Decided, Dmytro 2026-11-21): it needs an
  admin key Dmytro creates in the Anthropic Console.

**Docs**
- `docs-internal/metrics.md` or a new `docs-internal/usage.md`, the `/mcp-docs`
  entries, `docs/` where it says what the assistant can ask.

## Decisions

| # | Decision | By |
|---|---|---|
| 1 | The three meters and their prices; a test call is never observed minutes; the agent's replies are not counted | Decided (Dmytro, roadmap row, 2026-11-20) |
| 2 | Usage per workspace, agent and run, in units and dollars at list price | Decided (Dmytro, roadmap row) |
| 3 | Connexity's own model cost is recorded and not shown to customers | Decided (Dmytro, roadmap row) |
| 4 | A new tool, `get_usage`, not `get_dashboard` extended: the dashboard answers "how good are the agents", over 7, 30 or 90 days; usage answers "what did it cost", by month | Proposed |
| 5 | Usage is recorded in its own table, not worked out from calls on reading | Proposed |
| 6 | A call's minutes are rounded up to a whole minute per call | Decided (Dmytro, 2026-11-21, chose "Rounded up per call") |
| 7 | No call is recognised as a test call yet; every synced call counts | Decided (Dmytro, 2026-11-21, chose "Nothing yet") |
| 8 | Caller messages in a simulated call that stopped with an error count | Decided (Dmytro, 2026-11-21, chose "Count them") |
| 9 | Usage before this change is filled in from the calls and runs already stored | Decided (Dmytro, 2026-11-21, chose "Fill it in") |
| 10 | Connexity's own model cost is read from the database; no tool or screen for it | Decided (Dmytro, 2026-11-21, chose "Database only") |
| 11 | The daily comparison with Anthropic's cost report is a second pull request under this row | Decided (Dmytro, 2026-11-21, chose "Second pull request") |
| 12 | Each record keeps token counts by kind and the model, not only dollars | Proposed |

## Done when

- A real call of 95 seconds stored for an agent: `get_usage` shows 2 minutes, $0.06,
  for that agent and workspace; storing it again does not add to it.
- A call stored with the test source, and a simulated call, add no observed minutes.
- A simulated call that stopped with an error after 3 caller messages adds 3.
- After the migration, usage for the calls and runs stored before it is there.
- A run of 2 simulated calls with 5 and 4 caller messages: 9 messages, $0.18, on the
  run in `get_test_runs` and under its agent in `get_usage`.
- A second workspace sees none of it.
- Connexity's own cost is in the table and in no answer.
- The contract tests pass with the new tool and its input descriptions; `make check`
  passes.

## Out of scope

- Billing, plans, credits, top-ups, discounts, a monthly minimum.
- A usage screen (comes with Billing, design first).
- Voice simulation minutes being recorded (no voice simulations yet).
- The daily comparison with Anthropic's cost report (second pull request).
- Costs that are not per call: hosting and the database.

## Risks

- With no test calls recognised, a test made as a web call on the voice platform
  counts as observed minutes until that changes. Today every stored call is a phone
  call.
- Rounding up per call counts 235 minutes where 180 were spoken on today's data; the
  price page has to say "per started minute".
- Usage recorded now and billing built later may disagree if the rules change in
  between; the records keep units, not dollars, so prices can change freely.

## Outcome

Built as planned, on branch `usage-per-workspace`.

- **Table:** `usage_record` (migration `0044_usage_record`), one row per real call and
  per simulated call, found again by a `source_key` so nothing is counted twice. The
  migration fills in history with the same counting.
- **Recording:** a real call when it is stored and when a model check on it is paid
  for; a simulated call when it finishes.
- **Reading:** `get_usage` (new MCP tool, group "Usage", guide `usage`);
  `run_scenarios` says the price per caller message and the last run's cost;
  `get_test_runs` shows caller messages and list-price cost per run and per call.
- **Connexity's own cost:** on each row with the model and token counts by kind; in no
  answer.
- **Docs:** `docs-internal/usage.md`, the data model, the MCP tool table, the
  scenarios guide, the `/mcp-docs` entry with every input described.

**The 14 simulated calls without a cost** (hosted database, read only, counts only):
all 14 never ran. They have no transcript and no finish time, from runs that stopped
before reaching them. No model answered, so there is nothing to record. The other 49
have a cost.

### Deviations from the plan

- **`cost_usd` on a run and a simulated call changed meaning.** `get_test_runs`
  already had it, and it was Connexity's own model cost. It is now the list price of
  the caller messages, as decisions 2 and 3 say; `caller_messages` is new next to it.
  No screen showed it.
- **A simulated call that broke after its conversation ran** now keeps its transcript
  and is counted. Before, such a call stored only its error. Found in code review;
  it follows decision 8.
- **The judge's tokens** are now added to a simulated call's stored token counts,
  which held the simulated caller's only.
- **Recording is guarded:** a failure writing a usage record is logged and never
  stops a call or a simulated call being stored. The next store of a real call
  writes it; a simulated call's row would be missing.
- **Docs:** a new `docs-internal/usage.md`, not a section of `metrics.md`.

### Check results

- **Backend, through the API:** `app/tests/api/routes/test_usage.py`, 8 tests on the
  local test database with invented agents and calls (no separate play-through
  server): a 95-second call is 2 minutes and $0.06, stored twice counts once; a test
  call, a simulation and a call without length count nothing; a run of 2 simulated
  calls shows its caller messages and cost on the run and under its agent; an
  errored simulated call with 3 caller messages adds 3; a call that broke after the
  conversation still counts; calendar months; another workspace gets 404 and sees
  nothing; own cost is in the table and in no answer; the migration's fill-in equals
  what recording wrote.
- **MCP server:** contract tests pass with the new tool, group and guide.
- **Code review:** 8 findings, 6 fixed, 2 documented (rows filled in by the migration
  have no model name; a real call's row names one model of several).
- **`make check`:** every step passed (plan, backend lint, types, tests and coverage, MCP server tests, frontend lint and types, generated client fresh).

### Not done

- The daily comparison with Anthropic's cost report: second pull request (decision
  11).
- Screens: none, as planned.
