# Remove the old eval stack, the old CLI and the self-hosted connector

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Connexity is the product: no more rebuild"
  (10.198), pull request 1 of 2. This one deletes code. The second rewrites `README.md`,
  `docs/`, the `CLAUDE.md` files and the lifecycle guide, and splits `REBUILD.md`.
- **Design:** No UI change. No screen calls anything this removes.
- **MCP:** None needed. No tool is added, removed or changed; the MCP adapter calls only
  `/mcp/workspaces/...` and `/feedback`, and none of those routes go.

## Goal

The repo still carries the product Connexity used to be: agents edited and versioned
inside Connexity, eval configs scored by generic metrics with pass thresholds, a
command line tool that drove them, and a connector for self-hosted agents that nothing
can reach. None of it is used. The frontend calls none of its routes, the MCP adapter
calls none, and the scenario runner has its own path.

After this merges, the backend holds only what the product does today. Someone reading
the public repo finds no second, older product next to the working one (Dmytro,
2026-11-19: "i want to get rid of it so anyone checking it dont have impression its not
workable").

## Decisions

### In the roadmap row (Dmytro, 2026-11-19)

1. Delete `Environment`, the old judge metrics, custom metrics and pass thresholds.
2. Delete `AgentVersion`, the old CLI with `CLI_README.md` and its PyPI release
   workflow, and the old eval configs and commands ("agree"); the assistant works
   through MCP.
3. Keep the simulation runner that is in use.

### Decided while planning (Dmytro, 2026-11-20)

- **Two pull requests:** code deletion first, then the docs ("Two PRs").
- **The old runner goes too.** The row says to keep the orchestrator, but the scenario
  runner (`services/test_run.py`) replaced it on 2026-11-17 and it has refused runs of
  scenarios since. Dmytro approved the deletion list that includes it ("ok approve").
- **The self-hosted connector is deleted and planned again when a self-hosted stack is
  connected** ("Delete, rebuild later"). Replaces the 2026-10-06 decision to keep the
  custom endpoint runtime and the agent contract.
- **The migration drops the old tables and columns** ("drop and delete"), after Dmytro
  saw the list with the hosted row counts below.

### Proposed

- **The old columns on `agent` go as well** (accepted with the plan, "Accept, build").
  They were written only by the create-agent and draft routes this deletes:
  `endpoint_url`, `system_prompt`, `tools`, `agent_model`, `agent_provider`,
  `agent_temperature`, `prompt_type`, `has_draft`. Counted on the hosted database
  before building: 1 agent, none of these columns holds a value a current feature
  wrote (`tools` holds an empty JSON value on that one agent).
- **`eval_config` and `test_case` keep their table names.** They hold scenario sets and
  scenarios. Renaming them is a separate change with no user-visible effect.
- **`README.md` loses only its links to what is deleted here** (the CLI section, the
  eval docs, the examples). Its rewrite is pull request 2.

## Changes

### Deleted: named in the row

- **Environments:** the model, the `/environments` routes and their tests. Deleting an
  integration no longer checks for environments.
- **Agent versions owned by Connexity:** `AgentVersion`, and the draft, publish,
  rollback, version and diff routes. Versions as the product shows them are component
  versions read from the platform, and stay.
- **Old judge metrics:** `judge_metrics.py`, `predefined_metrics.py`,
  `metric_generator.py`, and the metric scoring in `judge.py`. The transcript formatter
  the rule judge uses moves next to it.
- **Custom metrics:** the model, the `/custom-metrics` and `/config` routes. Signing up
  no longer seeds default metrics for the workspace.
- **Pass thresholds:** `metrics_pass_threshold`, `cases_pass_threshold`, `JudgeConfig`
  and `MetricSelection` leave `RunConfig`. A new run of scenarios stops storing them.
- **The old CLI:** `backend/cli/`, `CLI_README.md`, the root `pyproject.toml` that
  packages it, `publish-pypi.yml`, `release-please.yml` with its two config files,
  `docs-internal/releases/pypi.md`, the `make cli` target, and its lines in the lint,
  format and CI scripts.

### Deleted: the old runner and its routes

- **The runner:** `orchestrator.py` and `run_manager.py`.
- **Comparison and analysis of runs:** `services/comparison.py`, `diff.py`,
  `analysis.py` and `models/comparison.py`.
- **The test case generator:** `services/test_case_generator/`.
- **REST routes and their crud:** `/runs`, `/eval-configs`, `/test-cases`,
  `/test-case-results`, and the old `/agents` routes (create, read, update, delete,
  drafts) with `provider_agent_import.py`. `/agents/list`, `/agents/{id}/page` and
  `/agents/{id}/tests` stay.
- **Scripts:** `test_run_sse.py`, `metric_generate_smoke.py`, `simulate_convo.py`.
  `compare_runs.py` stays: it was rewritten on 2026-11-17 for comparing two ways to
  decide a check.
- **Retell functions nothing calls:** the batch test, chat, chat agent and web call
  helpers in `services/retell.py` (13 functions).

### Deleted: the self-hosted connector

- `eval_runtimes/text/custom_endpoint.py` and its registry entry; Retell is the one
  runtime.
- `docs/agents/contract.md`, the `examples/` folder, and the custom endpoint part of
  `docs/evals/runtimes.md`.
- `ChatMessage` and `AgentResponse` stay; the Retell runtime uses them.

### Docs that describe what is deleted

- `docs/evals/judge-criteria.md`, `scoring-and-thresholds.md` and
  `test-case-schema.md` go.
- `docs-internal/data-model.md` and `docs-internal/testing.md` lose the deleted tables
  and files. `REBUILD.md` gets its status row; it is split in pull request 2.

### Database (one migration)

| What | Rows on the hosted database, 2026-11-20 |
|---|---|
| Table `agent_version` dropped | 0 |
| Table `environment` dropped | 0 |
| Table `custom_metric` dropped | 9, the defaults seeded at sign-up |
| Runs from before scenarios (no scope) | 0, so nothing to delete |
| Test cases that are not scenarios | 0, so nothing to delete |

Columns dropped, none of them read by current code:

- `run`: `agent_version_id`, `agent_version`, `is_baseline`, `aggregate_metrics`,
  `eval_config_version`, `name`, and the agent snapshot (`agent_endpoint_url`,
  `agent_system_prompt`, `agent_tools`, `agent_model`, `agent_provider`).
- `test_case_result`: `verdict`, `passed` and the latency columns.
- `test_case`: `difficulty`, `tags`, `evaluation_criteria_override`.
- `eval_config_member`: `repetitions`.
- `agent`: the Proposed list above.

What stays untouched on the hosted database: 1 scenario set, 18 scenarios, 1 run with
its 21 simulated calls.

### What an API caller notices

- The deleted routes answer 404.
- The generated frontend client shrinks; no screen changes.

## Done when

- `make check` passes.
- `git grep -n -w -E "AgentVersion|CustomMetric|JudgeConfig|custom_endpoint|orchestrator"`
  finds nothing in `backend/app`, `mcp_server` and `frontend` outside the migrations
  and the test that the custom endpoint runtime is gone.
- `backend/cli/`, `examples/` and `CLI_README.md` do not exist.
- On the local database the migration applies, downgrades and applies again, and
  `alembic check` reports no drift.
- Through the API on the local database: sign-up creates a workspace; an integration
  can be deleted; `write_scenarios`, `write_scenario_set`, `run_scenarios` and
  `get_test_runs` answer as before; `GET /agents/{id}/tests` answers as before; a
  deleted route answers 404.

## Out of scope

- The docs rewrite and the `REBUILD.md` split: pull request 2 of this feature.
- The word "1.x" in comments of files that stay: pull request 2.
- The `announce-release` and `tanstack-streaming` skills, which still use the CLI and
  Environments as examples: pull request 2.
- Renaming `eval_config` and `test_case`.
- Vapi and ElevenLabs sync, and `routes/integrations.py`: in use, they stay.
- Cloud Run and deploy settings.

## Risks

- **Coverage floor.** The deleted code is well tested, so removing it and its tests
  can move total coverage under 90%. If it does, tests are added for what stays; the
  floor is not lowered.
- **Deleted tests.** Tests of deleted code go with it. The pull request says so at its
  top, with the list. No test of code that stays is loosened.
- **A shared test helper creates `AgentVersion` rows** (`tests/utils/eval.py`), and 29
  test files use it. It is rewritten to create an agent the way `add_agents` does; a
  reviewer should check those tests still test the same thing.
- **The migration is not reversible in data.** Its downgrade recreates the tables and
  columns empty. The 9 seeded metric rows are lost; nothing reads them.
- **An unseen caller.** A script or person calling a deleted REST route gets 404. The
  frontend and the MCP adapter were checked; nothing else is known to call them.
- **Size.** More than 15,000 lines go, tests included. The review is of this list, not the diff.

## Outcome

About 33,700 lines removed and 1,100 added outside the generated client and the
lockfile; 150 files deleted, 39 of them test files.

### Deviations from the plan

- **`docs/evals/runtimes.md` is deleted whole,** not only its custom endpoint part. The
  rest described the old runner's routes and files. `docs/evals/` no longer exists.
- **More went than the list named, all of it code that lost its last caller:** the
  functions that imported an agent's prompt from Retell, Vapi and ElevenLabs
  (`import_*_config`, used only by the deleted create-agent route), the model catalogue
  (`llm_models.py`, used only by `/config`), the tool-definition and token-estimate
  helpers of the old runner and the connector, the schema classes of the old REST
  routes, and the settings `JUDGE_TEMPERATURE`, `ANALYSIS_*` and `GENERATOR_*`. Two
  dependencies nothing imports any more left `backend/pyproject.toml`: `httpx-sse` and
  `deepdiff`.
- **`run.name` and `agent.prompt_type` were dropped** with the listed columns; nothing
  read them.
- **`eval_config.config` stays.** It was not on the approved list. Nothing reads it.
- **`Agent.mode` now defaults to `platform`** (review finding): `endpoint` was the
  self-hosted mode.
- **Tests that created agents through the deleted `POST /agents/` now create the row
  directly** (`create_agent_as` in `tests/utils/eval.py`); the shared helper no longer
  makes an `AgentVersion`. Seven test files use it, not 29 as the plan said: the count
  included test files that were deleted. The shared text loop's three tests ran through
  the custom endpoint runtime and now run through a small test runtime.
- **`examples/fault-agent/` is still on Dmytro's machine.** It is ignored by git and
  was never in the repo; the tracked `examples/` files are gone.
- **The lockfile's `revision` went from 3 to 5,** because it was regenerated with the
  current `uv`. `uv` 0.5.11, which the backend image pins, reads it with `--frozen`
  (checked with `uv export --frozen`).

### Check results

`make check`, run once after the build:

| Step | Result |
|---|---|
| Plan present and complete | failed then, on the empty Outcome; passes with this section |
| Backend lint and format | ok |
| Backend types (pyright) | ok, 0 errors |
| Backend tests and coverage | ok: 997 passed, coverage above the 90% floor (96% on the full run before it) |
| MCP server tests | ok: 56 passed |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

After `make check`, the review's two small fixes (below) were made; lint, pyright and
the test files they touch were run again (75 passed), not the whole suite.

Migration `0040`, on a scratch local database: applies from `0039`, downgrades and
applies again, `alembic check` reports no drift. The downgrade ran on empty tables
only.

The API was exercised through the route tests (`TestClient` on the local database), no
separate server:

| Request | Expected | Came back |
|---|---|---|
| `GET` on `/agents/`, `/runs/`, `/eval-configs/`, `/test-cases/`, `/test-case-results/`, `/custom-metrics/`, `/environments/`, `/config/available-metrics` | 404 | 404 (new test) |
| Sign up, then `GET /workspaces/` | one open workspace, no metric rows seeded | as expected |
| `DELETE /integrations/{id}` | 200 without an environment check | 200 |
| `write_scenarios`, `write_scenario_set`, `run_scenarios`, `get_test_runs` | as before | as before (`test_scenarios.py`, `test_test_runs.py`, `test_test_results.py`) |
| `GET /agents/{id}/tests` | as before | as before (`test_tests_tab.py`) |
| `GET /agents/list` as another workspace | the other workspace's agent not listed | not listed |

Done-when greps: `git grep -n -w -E "AgentVersion|CustomMetric|JudgeConfig|custom_endpoint|orchestrator"`
finds one line, the test that the custom endpoint runtime is gone. `backend/cli/` and
`CLI_README.md` do not exist.

`/code-review` (high) reported 8 findings:

| Finding | What was done |
|---|---|
| `crud.list_agents` has no caller | Removed with its two tests |
| `Agent.mode` defaults to the deleted `endpoint` mode | Default is `platform` |
| Lockfile revision is past the `uv` the image pins | Checked: `uv` 0.5.11 reads it |
| Deleting an integration with linked agents hits the agent foreign key (500) | Not fixed: it predates this change. See Not done |
| The downgrade was not run with rows | Not done |
| Runtime methods with no caller (`validate_config`, `test_connection`, `supported_for_platform`) | Not done |
| `eval_config.config` is an unused column | Not done: not on the approved list |
| The plan gate still exempts `release-please--*` branches | Not done: it is a gate, changed only when asked |

For Dmytro to check on screen: nothing changed on any screen. Open the Agents list, an
agent's Tests tab and the Work page once to confirm they load as before.

### Not done

- The docs rewrite, the `REBUILD.md` split, the skills that use the CLI and
  Environments as examples, and "1.x" in comments of files that stay: pull request 2.
  `README.md` still describes the old product apart from the removed CLI and connector
  sections.
- Deleting an integration that has agents linked answers 500. Found by the review, not
  caused by this change, not fixed.
- The runtime interface's three uncalled methods, the always-empty `endpoint_url` on
  the runtime types, and the `eval_config.config` column are left.
- The migration's downgrade was not run on a database with rows.
- The migration has not run on the hosted database; it runs when the backend deploys.
- The screens were not looked at.
