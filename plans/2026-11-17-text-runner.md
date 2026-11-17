# Text simulation runner

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Text simulation runner" (10.1292). It comes
  after scenarios (10.1291, #220) and before test results (10.1293) and the Tests tab
  (10.1294).
- **Design:** `docs-internal/testing.md`, which wins over `designs/08-testing.md`.
  Nothing on screen here: runs show in test results (10.1293) and on the Tests tab
  (10.1294).
- **MCP:**
  - `run_scenarios` starts a run;
  - `get_test_runs` answers one run, or the agent's runs;
  - the scenarios guide gains "Running scenarios".

## Goal

The assistant runs an agent's scenarios on demand: a named set, a one-off pick, or every
scenario. A simulated caller talks in text to the agent's own engine, with the
scenario's tool results faked. Each scenario repeats several times. After each
conversation, one judge call gives every rule the scenario lists one of three verdicts:
Passed, Failed or Didn't come up. Code checks run on the same conversation. The assistant
reads back what passed, what failed and what is flaky, rule by rule. Whether a version
passes, and issues from the gate, come in test results (10.1293).

## Decided

These are Dmytro's words, in `testing.md`:
- **A scenario is a stage with no pass or fail of its own.** What counts is the total of
  rule verdicts (decision 5).
- **A run judges only the rules its scenario lists** (decision 9).
- **Code checks also run on simulated calls** (decision 10).
- **Named sets, and the assistant picks what to run** (decision 11), **or a one-off
  pick** (decision 13). **The gate runs every scenario** (decision 12).
- **Connexity uses AI for evals, never as an agent** (decision 2026-11-07). The runner
  talks to the agent's own engine; it never imitates the agent (2026-10-06).

## What exists

The 1.x eval stack is frozen but whole:
- **`orchestrator.execute_run`** runs every test case of an eval config, with its repeats,
  under a concurrency limit. It judges each transcript and stores a `test_case_result`
  per repeat, with costs and latencies. It runs as a task in the API process
  (`asyncio.create_task`), like the other background jobs here.
- **The Retell text runtime** (`eval_runtimes/text/retell.py`) talks to Retell's
  `agent-playground-completion`, one request per caller turn. It passes the test case's
  `user_context` as Retell's dynamic variables.
- **It fakes no tools.** Retell's playground takes `tool_mocks`, and Retell's docs say a
  tool call that matches no mock falls through to the real tool. So a 1.x run calls the
  agent's real tools, such as a real booking.
- **The custom endpoint runtime** talks to a team's own deployed service (Pipecat and
  similar). That service runs its own tools; the contract has no fakes.
- **The user simulator** is told the persona, the background and the expected outcomes
  as its goal. It does not know the new `caller_goal` and `caller_behaviour`.
- **The judge** scores the 1.x generic metrics (tool routing, grounding and the rest) and
  each expected outcome as pass or fail. A test case passes when all its outcomes pass.
- **Code checks are pure** (`checks/base.py`): they read a trace and its executions.
  `check_call` stores findings against a `call` row; `run_checks` runs them in memory.
- **`call.source` already has `simulation`**, but no query filters on it.
- **Retell's create-test-case-definition and batch-test calls** in `services/retell.py`
  are used nowhere.

## Changes

### What a run is

- **`run_scenarios`** runs one of three:
  - a named set;
  - a pick of scenario ids;
  - every active scenario of the agent.
- **Each scenario repeats** `repeats` times. The default is 3, and the most is 5
  (question 3).
- **At most 200 simulated calls per run.** A run over that is refused, naming the count.
- **The run records:**
  - what was run (the set's name, a pick, or all);
  - the spec version whose rules it judged;
  - the agent's version on the platform (question 4).
- **`run.eval_config_id` becomes optional:** a pick or "all" has no set.

### The conversation (Retell)

- **The simulated caller** is told who they are (`persona_context`), their goal
  (`caller_goal`), how they behave (`caller_behaviour`) and what they know
  (`user_context`). It is not told the rules: a caller who knows what is checked would
  steer the agent towards it.
- **The agent's variables** (`agent_variables`) go to Retell as dynamic variables, in
  place of `user_context`.
- **Who speaks first, the first message, the turn limit and the timeout** work as in
  1.x.
- **The version:** the playground request names the version the run tests.

### Faked tools (question 2)

- **The scenario's fake tool results** become Retell tool mocks:
  - the tool's name;
  - the expected arguments as a partial match, or any arguments when none are given;
  - the result as JSON.
- **No real tool ever runs.** Every other tool call gets a default fake, with the result
  `{"error": "This tool is not available in this test."}`. It is one catch-all mock
  without a tool name, which Retell's docs say matches every tool, sent after the
  scenario's fakes.
- **If the runner cannot cover every tool,** it refuses to start and says which tool is
  missing.
- **The run records each default fake that was used,** by tool. The judge is told that
  this tool was not available.

### Judging

- **One judge call per conversation.** The judge reads:
  - the transcript;
  - the scenario's listed rules with their text from the run's spec version;
  - the caller's goal.
- **The judge answers each listed rule** with Passed, Failed or Didn't come up, a reason
  of one or two sentences, and the turns it rests on.
- **A rule a newer spec dropped** is not judged; the run says so.
- **New runs do not use the 1.x generic metrics or the 1.x pass threshold** (question 6).

### Code checks

- **Each conversation becomes a trace in memory:** utterances, tool calls and the faked
  results. `run_checks` runs every check that is not off.
- **Checks that need timing or a recording are skipped** and recorded as skipped. Today
  none of the four checks needs them.
- **Findings are stored with the conversation, never as production findings** (question
  1). They become issues only from the gate (10.1293).

### Storage (question 1)

- **A repeat is a `test_case_result`,** as in 1.x: its transcript, costs and code-check
  findings. `passed` stays empty, because a scenario has no pass or fail.
- **A new table, `rule_verdict`:** one row per repeat and listed rule. It holds:
  - the run, the repeat and the scenario;
  - the rule key;
  - the verdict (passed, failed or didn't come up);
  - the reason;
  - the turns;
  - whether the rule was critical at the time.

  Test results (10.1293) count these rows by rule and version.

### MCP

- **`run_scenarios(workspace_id, agent_id, set? | scenario_ids? | all?, repeats?)`**
  - **Exactly one of** `set`, `scenario_ids` or `all` must be given.
  - **It starts the run and answers right away:** the run id, how many simulated calls
    it will make, and the next step, `get_test_runs`.
  - **It refuses, and stores nothing, when:**
    - the agent has no spec, or no scenarios;
    - the agent is not on Retell (question 5);
    - the workspace has no model key;
    - a tool cannot be faked;
    - the run is over 200 calls.
- **`get_test_runs(workspace_id, agent_id, run_id?)`**
  - **With a run id,** it answers the run's status and progress, then the rule totals:
    - failed rules first, critical first;
    - per rule, passed, failed and didn't come up across repeats;
    - "flaky" when a rule both passed and failed;
    - code-check findings by check.

    Then each scenario's repeats, paginated, with the judge's reasons for failures.
  - **Without one,** it answers the agent's runs, newest first, paginated.
- **The scenarios guide** gains "Running scenarios":
  - run a set or a pick while working on a change;
  - run all before a release;
  - a flaky rule needs another look;
  - every tool a scenario touches needs a fake, or it gets the default.

## Decisions

- Everything under "Decided" is Decided.
- **Questions 1 to 6 are Decided as recommended** (Dmytro, "Accept, build",
  2026-11-17).
- **Not in this PR:**
  - a task on Work (results bring the failed-version task, 10.1293);
  - the threshold and the version's verdict (10.1293);
  - model checks on simulated calls (open question 5 in `testing.md`).

## Questions

1. **Where a simulated call lives.** Recommend the repeat stays a `test_case_result`, with
   code-check findings on it and verdicts in `rule_verdict`. Nothing touches the `call`
   table, so production counts, issues and the call list cannot pick up a simulated
   call by mistake. The alternative is a `call` row with source `simulation`. It would
   open like any call and code checks would run unchanged, but every production query
   would need a filter first. Test results (10.1293) can still show a repeat as a call
   either way.
2. **Tools a scenario does not fake.** Recommend the default fake above, so no real tool
   ever runs and the run says where the default was used. The alternative is to refuse
   to run a scenario that touches a tool it does not fake. That is safer for the
   verdicts, but the assistant would have to fake every tool in every scenario.
3. **Repeats.** Recommend 3 by default and at most 5, with at most 200 simulated calls
   per run. Each repeat costs the platform's chat messages, the simulated caller and
   one judge call. Say other numbers.
4. **Which version is tested.** Recommend the agent's latest version on Retell, the one
   being edited, so a change is tested before it is published. The run takes a version
   number to test an older one. The alternative is the published version by default.
5. **Retell only for now.** Recommend Retell only: it is the only runtime that can fake
   tools. The custom endpoint runtime (Pipecat and similar) waits until its contract
   takes fakes, and is refused until then with a clear answer. The alternative is to run
   it now, against the team's real tools.
6. **The 1.x judge's generic metrics, custom metrics and pass thresholds.** New runs do
   not use them. Rule 7 says to ask before deleting what `REBUILD.md` does not list.
   Recommend that I add them to `REBUILD.md`'s demolition list and delete them in a
   separate PR, with the 1.x run screens' leftovers, so this one stays the runner. The
   alternative is to delete them here.

## Done when

- **Through the API,** in the route tests on the local database, with Retell's playground
  and the model mocked (`respx`):
  - a set, a pick and "all" each run every repeat;
  - each repeat stores a transcript and one verdict per listed rule;
  - Retell receives the agent's variables, the version and a mock for every tool;
  - no request reaches a tool unfaked;
  - code-check findings are stored on the repeat, and no `finding` or `call` row
    appears;
  - each refusal stores nothing;
  - `get_test_runs` answers the totals, flaky rules and pages.
- **Retell timeouts, empty answers and malformed answers** have tests, and so does the
  judge's malformed output.
- **One real run against a test agent on Retell,** if Dmytro names one. It shows that
  Retell takes the mocks and that no real tool was called.
- **`make check` passes** once, before the pull request.

## Out of scope

- The version's verdict, the threshold, gate issues and the failed-version task
  (10.1293).
- The Tests tab (10.1294).
- Audio and phone runs.
- The custom endpoint runtime, if question 5 goes as recommended.
- Deleting the 1.x judge metrics, if question 6 goes as recommended.

## Risks

- **A run lives in the API process.** A restart stops it partway. On start-up, runs left
  running are marked failed with "stopped by a restart"; the assistant runs them again.
- **Retell's rate limits are not documented.** Concurrency stays at 1.x's 5, and Retell's
  429 answers are retried as in 1.x.
- **The default fake changes how the agent behaves.** The judge is told, and the run
  names each tool that got it, so the assistant can add the missing fakes.
- **Retell's docs do not say which mock wins** when the scenario's fake and the
  catch-all both match. The scenario's fakes are sent first; a real run against a test
  agent shows which wins.

## Outcome

### Deviations from the plan

- **No refusal for a tool that cannot be faked.** The catch-all fake answers every tool,
  so no tool is ever left unfaked and the refusal has nothing to catch.
- **The default fakes come from the fakes that were sent,** not from what Retell
  echoes back. A tool call no scenario fake matches (by name and arguments, as Retell
  matches) got the default. Retell's docs do not say the playground echoes a mock's
  output.
- **"The latest" is pinned to a number** when the run starts: the runner reads the
  agent's versions from Retell. Every call of the run then talks to that version, and
  the run records it. If Retell does not answer, the run goes on against the latest
  and records no number.
- **A conversation the platform broke off is an error, not judged:** an error answer,
  a malformed answer, an empty answer, a timeout, or the call's time running out.
  1.x judged such transcripts.
- **The agent's variables are kept across turns.** The 1.x runtime replaced them with
  whatever Retell answered, so they were lost when Retell answered none.
- **The 1.x run route and orchestrator refuse a run of scenarios.** Without that, a
  failed run of a set could be started again through 1.x and judged by the old judge.
- **1.x runs on Retell also fake every tool now,** with the catch-all, because the
  runtime is shared. Before, they called the real tools.
- **The restart clean-up moved** into `crud.test_run.fail_stale_runs`, so it is tested.
- **Review findings:**
  - fixed: the 1.x route guard, default fakes from the fakes sent, the judge's
    timeout and empty answers tested, scenario names read in one query, and the
    pinned version;
  - no code change: the "cannot be faked" refusal, recorded above.

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
- `test_test_runs.py` (new), `test_scenarios.py`, `test_runs.py`, `test_test_cases.py`,
  `test_eval_configs.py`, `test_test_case_results.py`, `test_spec_api.py`,
  `test_next_task.py`, `app/tests/crud` and `app/tests/services`;
- the MCP server tests.

No separate play-through server: the route tests send the same requests through the API
on the local database, with Retell's playground and the model mocked.
- **A set, a pick and "all"** each store one simulated call per scenario and repeat.
  A set run makes every repeat.
- **Every request to Retell carries:**
  - the version;
  - the agent's variables;
  - the scenario's fake first, then the catch-all.
- **The simulated caller** is told the goal and behaviour and never the rules. The
  judge is told only the listed rules and which tools got the default fake.
- **Verdicts:** each simulated call stores one verdict per listed rule, with the mark
  the rule had. A rule that passed and failed is flaky, and a critical failure is
  counted.
- **Code checks** run on the conversation: `tool_call_failed` is found on a failed fake,
  and a default fake is no result, not a failure. No `call` or `finding` row appears.
- **Platform errors, malformed, empty and timed-out answers** end the simulated call in
  an error with no judge call. So do the judge's malformed, empty, incomplete and
  timed-out answers.
- **Refusals store nothing:**
  - no model key;
  - two scopes;
  - an unknown scenario;
  - an unknown set;
  - repeats out of range;
  - over the call limit;
  - an agent not on Retell;
  - no scenarios.
- **`get_test_runs`** pages the runs and a run's calls, says "Still running", and
  answers 404 for another agent's run.
- **A restart** fails the runs it stopped, and a failed run is not started again.
- **The 1.x run route** refuses a run of scenarios.

The 1.x Retell runtime tests now expect the catch-all fake and the version in each
request, and their fake test case has the scenario fields. Nothing was weakened.

Nothing on screen: runs show in test results (10.1293) and on the Tests tab (10.1294).

### Not done

- **No real run against a Retell agent.** No test agent was named. Two things wait for
  one:
  - which mock wins when a scenario's fake and the catch-all both match;
  - whether Retell answers the version query.
- **The hosted workspace has no model key,** so `run_scenarios` refuses there until a
  key is added. Nothing in 2.0 adds one yet; the 1.x company route still can.
- **Deleting the 1.x judge metrics:** listed in `REBUILD.md` for a separate PR.
- **The custom endpoint runtime,** until its contract takes fakes.
