# Prompt from the platform, simulations on Connexity's key

- **Owner:** Dmytro
- **Slice:** Roadmap 10.193, from testing feedback 2026-11-18 (items 1 and 7)
- **Design:** No UI change.
- **MCP:**
  - `get_spec`: `include_prompt` removed, with its contract entry and input
    description updated.
  - `get_spec`, `write_spec`, `get_next_task` and `get_agent`: next steps reworded.
  - `run_scenarios`: no longer refused for a missing model key.
  - Guides: `spec` and `getting-started` updated.

## Goal

Two fixes from Dmytro's testing.

1. **The assistant reads the agent's prompt from the voice platform, not from
   Connexity.** During onboarding it took the prompt from `get_spec` with
   `include_prompt`, because the spec task's steps told it to. Decided (Dmytro):
   Connexity never sits as a proxy between the assistant and the voice platform; its only
   place in that path is the deploy gate.
2. **Simulations run on Connexity's own model key.** `run_scenarios` refused the smoke
   test because the workspace had no model key. Decided (Dmytro, "I agree with connexity
   key and no BYOD"): the simulated caller and the judge use Connexity's key, and
   workspaces never bring one.

## Changes

**Prompt from the platform**

- **Every step, rule and guide that sent the assistant to Connexity's recorded prompt
  now tells it to read the prompt and config from the platform** (Retell, with its own
  access), for the version the agent's calls run on. That covers:
  - the onboarding "Write the spec" instruction;
  - the spec task's steps in `get_next_task`;
  - `get_spec`'s and `get_agent`'s next steps;
  - `guides/spec.md` and `guides/getting-started.md`.
- **Connexity still records each version's prompt itself,** from the calls it pulls, and
  still checks every quote in a rule against it. The rule changes to: quote the prompt of
  the version the calls run on (the published one, not a draft), or the quote is
  refused.
- **`include_prompt` is removed from `get_spec`,** with the `prompt` field on
  its answer, the MCP input and the contract entry. An old MCP server that still sends it
  is ignored by the backend, so the services can deploy in either order.

**Simulations on Connexity's key**

- **`run_scenarios` always runs:** the simulated caller and the judge use the backend's
  keys (`OPENAI_API_KEY`, already a secret in production). The "no model key" refusal
  goes.
- **The 1.x per-workspace model keys are deleted:**
  - `services/tenant_llm.py` and the ambient key context in `services/llm.py`;
  - the dependencies in `api/deps.py` that bind or require a key;
  - `GET/PUT /company/llm-credentials`;
  - the company's key fields, dropped by a migration (production stores none: 0 of 2
    workspaces);
  - the related parts of `initial_data.py`, `main.py`, the orchestrator and their tests;
  - the regenerated client.
- **The simulated caller and the judge switch to Claude Haiku 5.5** (`claude-haiku-5-5`),
  the model the judge checks use, in place of `gpt-4.1`.
- **No spending cap on simulations for now.** Each run stays capped at 50 simulated
  calls.

## Decisions

- **Decided (Dmytro, roadmap row):**
  - Connexity is never a proxy between the assistant and the platform.
  - Connexity's key, no bring-your-own key.
  - Delete the per-workspace keys.
- **Decided (Dmytro, 2026-11-18):**
  - Remove `include_prompt`.
  - The simulated caller and the judge run on Claude (Haiku 5.5).
  - No daily cap for now.

## Done when

- No task step, rule or guide mentions `include_prompt` or "the prompt Connexity
  recorded"; they name the platform. A test checks the spec task's steps and the
  onboarding instruction.
- `run_scenarios` on a workspace with no key starts a run, through the API in a test,
  with the model call mocked.
- Nothing in the backend, MCP server or frontend refers to a workspace model key;
  `make check` passes, and the migration drops the columns.

## Out of scope

- How the deploy gate works (Connexity's one place in the path, later).
- Credits and billing for simulations (Milestone 9).
- A spending cap on simulations (Dmytro: none for now).

## Risks

- **A quote from a draft prompt is refused** when the assistant reads the platform's
  draft instead of the published version. The rule and guide say which version to read.
- **Simulations spend Connexity's money** on any workspace that runs them. Each run is
  capped at 50 simulated calls today, but there is no daily cap.

## Outcome

### Deviations from the plan

- **The spec rules gain a line:** read the prompt from the voice platform, never from
  Connexity, for the version the agent's calls run on (`current_agent_version`), not a
  draft. Connexity checks quotes against the prompt it recorded for that version.
- **The model is set in two settings,** `SIMULATION_MODEL` (`claude-haiku-5-5`) and
  `SIMULATION_PROVIDER` (`anthropic`). The run stores the simulated caller's model in
  its config, so each run says what it ran on. Older 1.x evaluation paths still use the
  global default; scenarios do not go through them.
- **`/company/llm-credentials` was the whole `company` router,** so the router is
  deleted. No screen used it.
- **Seeding a local superuser no longer copies the keys** into its workspace, and its
  two tests are deleted.

### Check results

`make check` (after rebasing onto main with #234): every step ok. Route tests ran through the API on the local
database (`TestClient`), so no separate play-through server was used.

**Tests:**

- **`test_spec_api.py`:**
  - `get_spec` answers no prompt, even when an older MCP server asks with
    `include_prompt`.
  - Its next steps name the voice platform, and its rules say "from the voice
    platform, never from Connexity".
  - No spec task step, onboarding instruction or MCP guide mentions `include_prompt`.
- **`test_test_runs.py`:**
  - A run starts on a workspace with no key; the "no model key" refusal is gone.
  - The simulated caller and the judge are each called with `claude-haiku-5-5` on
    `anthropic`.
- **MCP server tests:** 53.

### Not done

- **Deploy window:** the migration drops five `company` columns. While the old backend
  still serves during the rollout, its reads of `company` can fail for a few seconds.
  Production holds no keys (0 of 2 workspaces), so no data is lost.
