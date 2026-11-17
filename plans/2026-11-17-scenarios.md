# Scenarios linked to spec rules

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Scenarios linked to spec rules" (10.1291).
  It comes after Critical rules (10.12905, #219) and before the text runner (10.1292),
  test results (10.1293) and the Tests tab (10.1294).
- **Design:** `docs-internal/testing.md` (#218, not merged yet), which wins over
  `designs/08-testing.md`. Nothing on screen here: scenarios show on the Tests tab
  (10.1294).
- **MCP:**
  - `write_scenarios`, `list_scenarios` and `write_scenario_set`;
  - a new guide, `connexity://guides/scenarios`;
  - `get_spec` gains, per rule, how many scenarios list it.

## Goal

The assistant writes the scenarios an agent is tested on, and Connexity stores them with
the spec rules each one expects to come up. A scenario is a stage for a simulated call:
- who calls, with what goal, and how they behave;
- what the caller knows, and the agent's variables;
- the tool results to fake.

It has no pass or fail of its own. The assistant groups scenarios into named sets and
picks what to run. The runner (10.1292) uses all of this.

## Decided

These are Dmytro's words, in `testing.md`:
- **No approval for scenarios; a person who disagrees asks the assistant to change one**
  (decisions 1 and 2).
- **A scenario is a stage with no pass or fail of its own.** What counts is the total of
  rule verdicts (decision 5).
- **A run judges only the rules its scenario lists** (decision 9).
- **Named sets as in 1.x, and the assistant picks what to run** (decision 11), plus
  one-off picks without a set (decision 13).
- **Connexity never generates scenarios; the assistant writes them** (decision
  2026-10-09).
- **Reshape the frozen 1.x test case and eval config models** (roadmap row; `REBUILD.md`).

## What exists

- **`test_case`** (1.x, frozen):
  - name and description;
  - `persona_context`, one block of text for the simulated caller;
  - who speaks first, and the first message;
  - `user_context`, one free JSON for what the simulator knows;
  - `expected_outcomes`, sentences the 1.x judge passes or fails;
  - `expected_tool_calls`, which already carries `mock_response`, a canned tool result;
  - agent (optional), source call, difficulty, tags, status (draft, active, archived),
    and a judge override.
- **`eval_config`** (a named set for one agent) with **`eval_config_member`** (a test
  case, its position and its repetitions per run).
- **The frozen eval stack** reads them: the user simulator, the judge, the orchestrator,
  the Retell text runtime and the CLI. Their 1.x routes still exist; no screen uses them.
- **Spec rules** have a key that stays the same across versions, and now a critical
  mark (#219).

## Changes

### The scenario

The tables keep their names, `test_case` and `eval_config`, until the runner (10.1292)
unfreezes the stack; MCP and the docs call them scenarios and sets (question 1). A
scenario written through MCP has:

- **a name,** and a description for people;
- **the caller** (question 2):
  - who they are (`persona_context`);
  - their goal (new `caller_goal`);
  - how they behave (new `caller_behaviour`);
- **what the caller knows** (`user_context`), kept apart from **the agent's variables**
  (new `agent_variables`), the values the agent's platform passes in, such as the
  caller's name in the CRM;
- **who speaks first, and the first message;**
- **the tool results to fake** (question 3): each a tool name, optionally the arguments
  it answers, and the result to return. They are stored as `expected_tool_calls` rows
  with their `mock_response`. Whether and how the runner fakes them is 10.1292's work
  (`testing.md` open question 2);
- **the rules it expects to come up,** as links: one or more keys of the agent's latest
  spec (question 4);
- **the agent,** required.

Left as they are, and not written through MCP:
- `expected_outcomes`: the rules replace them;
- difficulty, tags and the judge override;
- the source call, which MCP can set as `from_call_id` (a call of the same agent).

`testing.md` leaves these to decide when building the runner.

### The link to rules

- **A new table, `scenario_rule`:** scenario, agent and rule key.
- **Linked by key,** so a scenario keeps its rules as the spec gets new versions. A key
  the latest spec no longer has leaves the scenario listing a rule that is gone.
  `list_scenarios` says so, and the assistant rewrites or archives it.

### Sets

- **A set is an `eval_config`:** a name, a description, and its scenarios in order.
  `repetitions` stays at 1 here: how many times a run repeats each scenario is the
  runner's choice (10.1292).
- **One-off picks** are a list of scenario ids passed to the runner; nothing is stored
  for them here.

### MCP

- **`write_scenarios(workspace_id, agent_id, scenarios[])`:**
  - Each scenario has the fields above.
  - Given its `id`, it replaces that scenario; with `archive: true` it is archived
    (status `archived`) and leaves every set.
  - Up to 20 per call. Every problem is listed, and nothing is stored when there is one,
    like `raise_clarifications`.
  - Refused:
    - an agent without a spec;
    - a scenario that lists no rule, or a key the latest spec does not have;
    - a fake tool result without a tool name;
    - a `from_call_id` that is not one of this agent's calls.
  - Next steps: put the new scenarios in a set (`write_scenario_set`), and name the
    critical rules no scenario lists.
- **`list_scenarios(workspace_id, agent_id, rule_key?, set?, cursor, limit)`:**
  - the agent's scenarios with their rules, each marked critical or gone;
  - the agent's sets with their scenario ids;
  - counts: scenarios, rules listed by at least one, critical rules listed by none.
  - Paginated.
- **`write_scenario_set(workspace_id, agent_id, name, scenario_ids, description?)`:**
  - creates the set, or replaces the set of that name;
  - an empty `scenario_ids` archives it.
- **`get_spec`:** each rule gains `scenarios`, how many active scenarios list it. This
  is not coverage: coverage counts rules a run checked (10.1294, `testing.md`).
- **Next steps:**
  - `write_spec` and `mark_critical_rules` end with "Write scenarios for the rules no
    scenario lists (`write_scenarios`)" when there are any;
  - that line names critical rules first.

### The guide: `connexity://guides/scenarios` (question 5)

How to write one:
- **A stage, not a test:** set up a caller who leads the agent to where the listed rules
  apply. The judge gives each listed rule Passed, Failed or Didn't come up.
- **List every rule the call should touch,** usually two to five, never a rule the
  scenario cannot reach.
- **Something no rule covers is a gap in the spec,** not in the scenario. Add the rule
  with `write_spec`, or raise a clarification, before writing the scenario.
- **The caller:**
  - who they are, in a line;
  - one goal;
  - how they behave, such as in a hurry, unsure, or pushing back.
- **Knowledge and variables apart:** what the caller knows (their policy number) is not
  what the agent is given (the CRM's name for them).
- **Fake the tool results the conversation needs,** with realistic values, never real
  callers' data.
- **Every critical rule in at least one scenario,** and the rules about money, safety
  and compliance in two:
  - one where the rule applies;
  - one where the caller pushes against it.
- **Sets:**
  - a "smoke" set of a few scenarios that touch the critical rules;
  - one set per area the assistant changes often;
  - the gate runs every scenario, so sets are for the assistant's own runs.

### Tasks (question 6)

- **A Scenarios task per agent** whose latest spec has rules no scenario lists: "Write
  scenarios for 12 rules on Front desk".
  - It comes in setup, after the agent's spec, which blocks it.
  - It is done when every rule is listed by a scenario.

## Decisions

- Everything under "Decided" is Decided.
- No screen here (rule 14): scenarios show on the Tests tab (10.1294).
- **The 1.x routes and the CLI for test cases and eval configs stay as they are:** they
  are frozen until the runner.
- Everything under "Questions" is Proposed until Dmytro answers.

## Questions

1. **Keep the table names for now.** Recommend keeping `test_case` and `eval_config`,
   and calling them scenarios and sets in MCP and the docs. The runner (10.1292)
   unfreezes the stack that reads them, and can rename them with everything that reads
   them. The alternative is renaming now, which touches the frozen orchestrator, judge,
   CLI and their tests in a feature that does not run them.
2. **The caller in three fields:** who (the existing `persona_context`), goal and
   behaviour (new columns). Recommend it, as `testing.md` proposes. The simulator joins
   them into its prompt. The alternative is one text block as in 1.x.
3. **Fake tool results stored as `expected_tool_calls` rows** with `mock_response`.
   Recommend it: the shape already holds a tool, the arguments it matches and a result.
   The alternative is a new column. Either way, faking itself is the runner's (open
   question 2).
4. **Linked by rule key,** not by one spec version's rule row. Recommend the key, which
   stays the same across versions: a scenario keeps its rules at each new version, and
   a dropped key is reported for the assistant to fix.
5. **The guide's rules above,** especially two scenarios for money, safety and
   compliance rules, and the smoke set. Recommend them as written; say what to change.
6. **A Scenarios task on Work** while rules have no scenario, after the spec and
   blocked by it. Recommend it, so the assistant reaches scenarios on its own after
   the spec. The alternative is no task until the runner exists.

## Done when

- **Through the API,** in the route tests on the local database:
  - `write_scenarios` stores scenarios with their caller, knowledge, variables, fake tool
    results and rule keys;
  - it replaces by id and archives;
  - it refuses unknown keys, no rules, other workspaces' agents and calls, and an agent
    without a spec, storing nothing;
  - a new spec version keeps the links of kept keys, and a dropped key is reported;
  - `list_scenarios` filters by rule and set, and pages;
  - `write_scenario_set` creates, replaces and archives a set;
  - `get_spec` answers each rule's scenario count;
  - the Scenarios task appears for rules without a scenario, blocked by a spec to
    write, and leaves when every rule is listed.
- **The frozen eval stack's tests still pass,** showing the reshape left it working.
- **`make check` passes** once, before the pull request.

## Out of scope

- Running scenarios, repeats, faking tools and the judge (10.1292).
- Results, thresholds and coverage (10.1293, 10.1294).
- Renaming the tables, and deleting 1.x fields or `test_case_generator` (question 1;
  rule 7).
- Audio and phone simulation.

## Risks

- **The 1.x routes can still write test cases** without rules or an agent. No screen
  uses them, and `list_scenarios` shows only scenarios with an agent and rules. The
  runner (10.1292) decides whether those routes stay.

## Outcome

### Deviations from the plan

- **Built on `critical-rules`** (#219, merged since): scenarios read the critical marks.
  The migration is `0029_scenarios`, after `0028_spec_rule_critical`.
- **A scenario is a `test_case` of the agent with at least one rule link.** The 1.x test
  cases without links stay out of `list_scenarios`, its counts and the Work task.
- **Replacing an archived scenario by id** makes it active again, outside any set.
- **`write_scenario_set` with no scenarios** archives the set (`deleted_at`) and empties
  it. It refuses scenarios that are not the agent's active ones.
- **`list_scenarios` names the set by `set`,** as the plan says. It answers 404 for a
  set the agent does not have.
- **`test_next_task.py`'s review test** now moves the review to the top through the
  person's order. The two Scenarios tasks above it kept trading places as returned
  tasks do, so walking the list never reached it. The test still checks that a review
  is done once handed out.
- **Review findings, all fixed:**
  - the Work list reads every agent's rules in one query;
  - `work_list`'s docstring;
  - "1 critical rule still has no scenario".

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
- `test_scenarios.py` (new), `test_critical_rules.py`, `test_spec_api.py`,
  `test_spec_tab.py`, `test_mcp_clarifications.py`, `test_work_page.py`,
  `test_next_task.py` and the schema conventions tests;
- the frozen eval stack's tests: `test_test_cases.py`, `test_eval_configs.py`,
  `test_runs.py`, `test_test_case_results.py` and `app/tests/services`;
- the MCP server tests.

Then the full `make check` ran once (CLAUDE.local.md). No separate play-through server:
the route tests send the same requests through the API on the local database.
- **`write_scenarios`** stores the caller, goal and behaviour, what the caller knows, the
  agent's variables, who speaks first, fake tool results and the rule links. It
  replaces by id and archives (the scenario leaves its sets).
- **Refusals** list every problem and store nothing:
  - no rules, an unknown key or an empty name;
  - a fake tool result without a tool;
  - another agent's call, or an unknown or missing id;
  - an agent without a spec;
  - another workspace (404).
- **`list_scenarios`:**
  - filters by rule and by set, and pages;
  - names the rules without a scenario, critical first;
  - after a spec drops a rule, shows it as gone, and the kept rule stays linked.
- **`write_scenario_set`** creates, replaces in order, refuses an archived scenario, and
  archives with an empty list.
- **`get_spec`** answers each rule's scenario count. `write_spec`'s next steps name the
  rules without one.
- **On Work,** "Write scenarios for 2 rules on Front desk" appears after the first scan.
  A spec needing review blocks it, and it leaves when every rule is listed.

Nothing on screen: scenarios show on the Tests tab (10.1294).

### Not done

- Running scenarios, repeats, faking tools and the judge (10.1292).
- Renaming the tables and deleting 1.x fields or `test_case_generator` (question 1).
