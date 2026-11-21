# Simulations check the agent's real tool schemas

- **Owner:** Dmytro
- **Slice:** "Simulations apply the agent's real tool schemas" (roadmap, Test stage)
- **Design:** No UI change.
- **MCP:** `get_test_runs` is extended (no new tool, no new input): schema violations per
  simulated call and per run, and `tool_schemas_applied` is replaced by
  `tool_schemas_checked`. Its rules, the scenarios guide and the `/mcp-docs` entry
  follow.

Status: **approved by Dmytro on 2026-11-20 ("merged, build")**. Statements are marked
Decided (Dmytro, from the roadmap row as updated on 2026-11-20), Proposed (Claude) or
Open.

## What was found before planning

Read from Retell's public documentation on 2026-11-20.

- **Retell documents no check of a tool call's arguments against the tool's schema.**
  The schema is guidance for the agent's model ("LLM will do its best to generate the
  required properties"). No rejection is described, and no error sent back to the
  agent for invalid arguments.
- **A text run already gives the agent's model its real schema.** Only the tool's
  answer is faked. So the schema's effect on what the agent sends is exercised today;
  what is missing is anyone looking at the arguments.
- Before the schema fix that started this row, empty values went through to real
  bookings: nothing refused them.

## Goal

A run says, for every tool call the agent made, whether its arguments obey the schema
of the version under test. A fix made in a schema can then be confirmed or disproved:
before the fix the run shows the violation, after it the run shows none.

## Changes

**Reading the schemas**
- The runner already reads the tested version from Retell when a run starts. It now
  keeps each tool's `parameters` schema from that same read.
- Only tools that declare a schema of their own are checked (Retell's custom tools).
  A hang-up, a transfer and Retell's built-in tools have none.

**Checking the arguments**
- After a conversation, every tool call's arguments are validated against its tool's
  schema: required fields, types, `minLength`, `pattern`, `enum` and the rest of JSON
  Schema.
- A violation names the tool, the field and what is wrong:
  "`schedule_appointment`: `postalCode` is empty, the schema asks for at least 1
  character".
- Nothing is sent back to the agent, and the fake answers as it does today (Decided).
- The judge is not shown the violations: it judges spec rules, as today (Proposed).
- A schema Retell accepted but the validator cannot read is reported once per run as
  "could not be checked", never as a violation.

**What a run says**
- Each simulated call lists its `schema_violations`, with the turn of the tool call.
- Each run counts calls with a violation and names the tools and fields, most frequent
  first, and leads its next steps with them.
- A violation does not change a full run's verdict or an on-demand run's result
  (Decided). The existing critical check for bookings with missing or placeholder
  details still fails the real harm.
- `tool_schemas_applied` (always false since the previous feature) is replaced by
  `tool_schemas_checked`: how many of the agent's tools had a schema and were checked,
  or why none could be (Retell could not be read). "Applied" would now claim more than
  is done: nothing is enforced.
- The rule line changes with it: a run with no violations shows the agent sent
  arguments that obey the schema in these conversations; it does not show the
  platform would refuse a bad one.

**Data**
- One migration: `test_case_result.schema_violations` (JSON). Nothing is backfilled;
  earlier runs show none and say their schemas were not checked.

**Docs**
- `docs-internal/testing.md`, the scenarios guide, `/mcp-docs`.

## Decisions

| # | Decision | By |
|---|---|---|
| 1 | Check every simulated tool call's arguments against the schema of the version under test, and report each violation per call and per run | Decided (Dmytro, roadmap row, 2026-11-20) |
| 2 | Nothing is sent back to the agent; no invented rejection | Decided (Dmytro, roadmap row, 2026-11-20) |
| 3 | A violation does not change the verdict; reported only | Decided (Dmytro, roadmap row, 2026-11-20) |
| 4 | No static check for required text fields without `minLength` | Decided (Dmytro, roadmap row, 2026-11-20) |
| 5 | `tool_schemas_applied` is replaced by `tool_schemas_checked`, not kept beside it | Proposed |
| 6 | The judge is not shown the violations | Proposed |
| 7 | Violations are stored on the simulated call, not as code-check findings, so they never count toward a critical code check | Proposed |

## Done when

- A scenario whose agent sends an empty required field: the call lists the violation
  with tool, field and turn; the run counts it and its first next step names it; the
  run's verdict or result is what it would be without it.
- The same scenario with valid arguments: no violation, and the run says how many
  tools were checked.
- A tool without a schema is not reported.
- A schema the validator cannot read: "could not be checked", no violation.
- Retell unreadable when the run starts: `tool_schemas_checked` says none, with why.
- `make check` passes.

## Out of scope

- Sending a rejection to the agent (decision 2).
- A static check of schemas (decision 4).
- Schemas enforced by the client's own backend (n8n, a CRM).
- Checking tool arguments on real calls. The same check could run there; it would be
  a new check in the library, added only when Dmytro asks for it by name.
- Any change to the Tests tab or the call screen. A violation reaches people through
  the assistant.

## Risks

- A validator stricter or looser than the model's own reading of the schema reports
  violations as facts about the arguments. It never claims the platform would have
  refused them, and the rule line says so.
- Renaming `tool_schemas_applied` one feature after adding it changes the contract
  again; an assistant with the old guide reads a field that is gone.
- Conversation-flow agents keep tools on nodes; if a tool's schema is not where the
  reader looks, that tool is reported as not checked, not as clean.

## Outcome

### Deviations from the plan

- **The column is `schema_check`, not `schema_violations`.** It holds the violations
  and also which tools had a schema and which could not be read, so a run can say what
  was checked. A call that was not checked has none, which is how "not checked" is told
  from "checked, nothing found".
- **A tool declared in several states with different schemas** is checked against any
  of them: a call obeys the tool when it obeys one. Found in code review; the first
  schema alone would have missed violations.
- **A schema the validator cannot follow** (a reference it cannot resolve) makes that
  tool "not checked" for the call instead of failing the call. Found in code review.
- **A violation's words carry no lengths of the value** ("is too short", not "has 4
  characters"), so the same problem counts once per call across a run. Found in code
  review.
- **A version's results also name the full run's violations,** beside the verdict they
  never change. The plan said only the run would. Found in code review.
- **`jsonschema` is now a declared dependency** of the backend. It was already
  installed through another package.
- **At most 50 violations are kept per simulated call,** so a looping conversation
  does not store hundreds.

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
| Full run on a version whose booking tool requires `date` and `name`, the agent sends only `date`; `GET test-runs?run_id=` | the call lists `book_slot`, `name`, "is missing; the schema requires it", turn 2; the run counts 1 call with a violation, 1 tool checked; first next step names it; a rule line explains it | as expected |
| Same run: what the agent got back | the scenario's fake, unchanged; no code-check finding | as expected |
| The same run on a version whose tools declare no schema | same verdict, result, totals and counts; checked, 0 tools, no violations | as expected |
| A run whose version could not be read at start | `tool_schemas_checked` false, no `schema_check`, a next step says so | as expected |
| Checker: empty required text, pattern, missing field, enum, wrong type, arguments not JSON | each in plain words, with tool, field and turn | as expected |
| Checker: a schema that is not JSON Schema, and one with a reference it cannot resolve | that tool not checked, no violation, other tools still checked | as expected |
| Checker: a tool declared in two states with different schemas | arguments obeying either pass; arguments obeying neither are reported once | as expected |
| Reader: tools of the tested version | schemas kept for tools that declare one; none for a hang-up or an empty schema | as expected |

One existing assertion was removed with the field it checked
(`tool_schemas_applied`), replaced by the tests above.

### Not done

- **Not run against a real agent.** The tests use invented tools and schemas. The
  first run on production after merge shows whether real schemas read and check as
  expected; a tool that does not is reported as not checked, not as clean.
- **The Tests tab and the call screen show no violations** (see Out of scope).
- **Calls made before this change** are not checked; their runs say so.
