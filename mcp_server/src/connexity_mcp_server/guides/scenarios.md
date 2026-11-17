# Writing and running scenarios

A scenario is the stage for a simulated call: who calls, what they want, how they
behave, what they and the agent know, and what the agent's tools return. It has no pass
or fail of its own. A run judges each rule the scenario lists: Passed, Failed or Didn't
come up. You write scenarios; Connexity stores them and never writes one itself. People
do not approve them: a person who disagrees asks you to change one.

## Before you write

- **The agent needs a spec.** Every scenario lists rules of its latest spec, by key.
  Call `get_spec`: each rule says how many scenarios list it (`scenarios`).
- **Something no rule covers is a gap in the spec,** not in the scenario. Add the rule
  with `write_spec`, or raise a clarification, then write the scenario.
- **Call `list_scenarios`** first: rewrite a scenario that is close instead of writing a
  second one.

## How to write one

- **List the rules the call should touch,** usually two to five. Never list a rule the
  scenario cannot reach: it will only ever read "Didn't come up".
- **The caller, in three parts:**
  - `caller`: who they are, in a line ("A policyholder renewing for the third year");
  - `caller_goal`: one goal ("Renew, but only if the price did not go up");
  - `caller_behaviour`: how they behave ("In a hurry, pushes back on the first price").
- **Lead the caller to where the rules apply.** A scenario for "Never quote a price
  above the quote lookup" has a caller who asks for the price and argues about it.
- **What the caller knows and what the agent is given are apart:**
  - `caller_knows`: what the simulated caller can say (their policy number, their
    date of birth);
  - `agent_variables`: what the agent's platform passes in (the name in the CRM, the
    clinic's opening hours).
- **Who speaks first,** and the first line, as the real agent's calls start.
- **Fake the tool results the conversation needs** (`fake_tool_results`): the tool, the
  arguments it answers when it matters, and the result. Use invented, realistic values,
  never a real caller's data.

## How many

- **Every critical rule in at least one scenario.** `list_scenarios` names those
  without one (`unlisted_rules`, critical first).
- **Rules about money, safety and compliance in two:**
  - one where the rule applies;
  - one where the caller pushes against it.
- **Then every other rule,** grouped into few scenarios: a scenario can prove several
  rules.

## Sets

- **A named set** is a list of scenarios you run together (`write_scenario_set`).
- **Keep a small "smoke" set** over the critical rules, and one set per area you change
  often.
- **The gate runs every scenario,** so sets are for your own runs. You can also run a
  one-off pick of scenarios without a set.

## Changing them

- **Replace a scenario** by passing its `id` with the whole scenario.
- **Archive one** with its `id` and `archive: true`; it leaves its sets.
- **When the spec drops a rule,** scenarios that list it show it as `gone`: rewrite them
  with the spec's keys, or archive them.

## Running scenarios

- **`run_scenarios`** runs one of three on the agent (on Retell for now):
  - a named `set`;
  - a pick of `scenario_ids`;
  - `all` of them.
- **Each scenario repeats** (`repeats`, 3 by default, at most 5). A run makes at most
  200 simulated calls.
- **`version`** picks the agent's version on its platform. The default is the latest
  one, the one being edited.
- **Run a set or a pick while you work on a change.** Run `all` before a release.
- **The run happens in the background.** Call `get_test_runs` with its `run_id` until
  it is completed.
- **No real tool runs:**
  - each tool call is answered by the scenario's fake result;
  - a tool the scenario does not fake answers that it is not available in this test,
    and the run names it under `default_fakes`;
  - add a fake for it with `write_scenarios` when the conversation needs a real-looking
    answer.

## Reading a run

- **`rules`** has every judged rule's totals across repeats: failed first, critical
  first.
  - "Didn't come up" is not counted.
  - A rule that both passed and failed is `flaky`. A flaky critical rule counts as
    failed.
- **Each simulated call** has its verdicts with the judge's reason and the turns it
  rests on. It also has what code checks found; that never counts as a production
  issue.
- **When a rule fails:**
  1. Read the reason and the turns.
  2. If the scenario is wrong (it led the caller somewhere the rule does not apply),
     fix the scenario.
  3. Otherwise the agent is wrong: tell the person what failed and what you suggest.
     Connexity never changes the agent.

