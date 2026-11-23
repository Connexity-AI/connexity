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
  one, the one being edited, read before the run is stored; when Retell cannot be read
  the run is refused and you try again.
- **Run a set or a pick while you work on a change.** Run `all` to verify a version:
  only a full run decides its verdict.
- **What a run counts.** Each message the simulated caller sends counts at list
  price; nothing is billed. `run_scenarios` says the price and what the last run of
  the same scenarios came to, `get_test_runs` shows each run's `caller_messages` and
  `cost_usd`, and `get_usage` the period's total.
- **The run happens in the background.** Poll it with `get_test_runs`, its `run_id`
  and `status_only`: the answer is the status and counts alone, and is cheap.
  - `queued`, `running` and `finished` say how far it is. A slow run still has calls
    running.
  - `stalled` means the server running it has given no sign of life for 2 minutes,
    most often a deploy. It is marked failed after 15; start it again then. Calls that
    finished keep their verdicts.
  - Read the run without `status_only` once it is completed.
- **A run makes up to 25 simulated calls at once.** `throttled` counts the platform's
  "too many requests" answers; the calls wait and go on.
- **No real tool runs:**
  - each tool call is answered by the scenario's fake result;
  - a tool the scenario does not fake answers that it is not available in this test,
    and the run names it under `default_fakes`;
  - a verdict that rests on that made-up answer is not evidence: it is marked (`mark`
    `default_fake`, the tools in `mark_detail`) and not counted. Do not act on it;
  - add a fake for it with `write_scenarios`, then run again.
  - a hang-up or a transfer ends the conversation there, as on a real call.
- **A conversation ends** when the agent hangs up or after 40 agent replies, and is
  judged on what was said. One still going after 10 minutes is stopped as an error.
- **Tool arguments are checked against the tool's own schema.** The agent's model
  gets its real tool schemas in a text run; Connexity then looks at what it sent.
  - `schema_violations` on a call, and `schema_check` on the run, name each tool and
    field that breaks its schema: a required field missing or empty, a pattern not
    matched.
  - A violation is a fact about the arguments. Nothing refused it, on a real call
    either: the schema only guides the model. Connexity sends nothing back to the
    agent, and a violation never changes the verdict.
  - To confirm a fix to a schema or a prompt, run the scenarios again: the violation
    is gone.
  - `tool_schemas_checked` is false when the tested version could not be read; run
    again.
- **A run is refused** when Connexity's model key is missing. Tell the person; there is
  nothing for you to fix.

## Reading a run

- **`rules`** has every judged rule's totals across repeats: failed first, critical
  first.
  - "Didn't come up" is not counted.
  - A rule that both passed and failed is `flaky`. A flaky critical rule counts as
    failed.
- **Each simulated call** has its verdicts with the judge's reason and the turns it
  rests on. It also has what code checks found; that never counts as a production
  issue.
- **What limits a run** comes first in its next steps. Read it before the results:
  - `content`: `same` when the version still has the content the run tested, read on
    the platform when you ask; `edited` when the same version number now does something
    else, so the run no longer describes it; `unknown` when it could not be read, which
    is never "the same";
  - `spec_version` is the spec the run judged against, and `spec_written_for` the
    agent version its rules were written for. `spec_behind` means the run tested a
    newer agent version: update the spec, or confirm nothing in it changed.
- **The sample** comes first when calls were lost: "18 of 21 calls judged, 2 stopped,
  1 judge error". `errors` counts calls that gave no verdicts; `judge_errors` are the
  ones with a conversation the judge could not answer for. An on-demand run that lost
  calls and found no failure is `incomplete`, not passed: run those scenarios again.
- **`timing`** says where a call's time went, as medians: the agent's platform, the
  simulated caller, the judge, and Connexity's own server. When the server's share is
  over a third, the run was slow because of Connexity, not the agent; its results
  stand.
- **When a rule fails:**
  1. Read the reason and the turns.
  2. If the scenario is wrong (it led the caller somewhere the rule does not apply),
     fix the scenario.
  3. Otherwise the agent is wrong: tell the person what failed and what you suggest.
     Connexity never changes the agent.

## A version's results

- **`get_test_runs` without `run_id`** answers one version's results: the newest
  tested version by default, live or not (a draft ahead of the live one is tested
  before it goes live), or `version`. `live` gives the live version's state beside it.
- **Verified belongs to the content that passed.** On Retell a draft is edited under
  the same number: a version is judged by the latest full run of what it does now (its
  newest run's content). Edited after its full run, it is not verified until a new full
  run (`edited_since`). The same content under another number is judged by that
  number's full run (`same_content`).
- **Only a full run decides the verdict.** A run of `all` is full; a set or a pick is on
  demand and never changes it. The verdict comes from the version's latest completed
  full run:
  - **Verified:** every rule of the spec checked (Passed or Failed) and nothing
    critical found. Non-critical failures do not fail it; tell the person which;
  - **Failed:** a critical rule failed (flaky included) or a critical code check found
    something;
  - **Partially tested:** nothing critical, but some rule was not checked (`unchecked`
    says whether it didn't come up, has no scenario, or was judged only on a default
    fake);
  - **Not verified:** no completed full run of this version, or one that judged no
    rule. `last_verified` names the newest other version a full run verified.
- **Verify a version before it ships.** Run `all` on the draft (the newest version on
  the platform, or `version`), then read its verdict here. Verified and not live: it
  passed the gate and can be published. Failed and not live: publishing it would be an
  override, which only a person decides. Connexity never publishes.
- **After it ships,** mark the issues it fixes with `mark_issue_fixed`; `get_issue`
  then says how many real calls there were since the version went live and how many
  still have the issue (`connexity://guides/issues`).
- **Each run** has its version and its `totals`: rules passed, failed, didn't come up
  and without a scenario, each counted once per run. Calls that stopped with an error
  count in no column (`not_judged` for rules only they listed), and so do rules judged
  only on a default fake (`default_fake`); a run no judge read
  (`judged_calls` 0) has no result; critical findings; calls stopped. And who ran it:
  the person, the assistant, the session (`session` on `run_scenarios`).
- **`stopped`** counts the full run's simulated calls that ended in an error, with the
  most common error and a run to open. They gave no verdicts.
- **Show the person a simulated call** with its `url`: it opens on the call screen,
  with the rules it was judged on.
- **Coverage** (`coverage`) is tests written: the share of the latest spec's rules that
  at least one active scenario lists. `coverage.uncovered` lists the rest, critical
  first.
