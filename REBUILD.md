# Connexity 2.0 rebuild plan

This is the working plan for turning Connexity 1.x into Connexity 2.0. Every rebuild
session starts here.

- **Why and what:** [`Connexity 2.0.md`](./Connexity%202.0.md) (the vision). This plan
  does not repeat it. Section numbers below (§) refer to that file.
- **How we work:** [`docs-internal/development-lifecycle.md`](./docs-internal/development-lifecycle.md).
- **This file:** the order of work, the current status, and the decisions made along
  the way.

When the vision and this plan disagree, the vision wins and this plan gets fixed.

---

## 1. Ground rules (decided 2026-10-06)

| Decision | Choice |
|---|---|
| Where the rebuild happens | In place, in this repo. Keep the chassis, delete the builder surface, add new modules. |
| Compatibility | None owed. Schemas, API, CLI and docs may break freely. No migration paths for 1.x data. |
| Who builds | Dmytro plus Claude Code. One human approving, agent sessions executing. |
| First milestone | Reference agent 1 (an outbound offer bot on Retell + n8n + GoHighLevel) at ladder levels 1 and 2: Observe and Check. |
| Reference agents | Reference agent 1 is the first example, not the centre of the design. More will be added on other stacks. |

**Building against one example without overfitting to it.** Milestone 1 is proven on
reference agent 1, but every slice is designed for any stack:

- Provider, backend and CRM specifics live in mapping and connector modules. The
  canonical schema, the check engine, the inbox and the UI never name Retell, n8n or
  GoHighLevel.
- Checks are written against the canonical trace. A check that only makes sense for
  one agent's business (prices, offers) is a per-agent parameterisation of a generic
  check, not a new built-in.
- When a design choice is being made only because reference agent 1 needs it, say so in
  the PR and ask whether a second stack would need something different.

Order of work follows the ladder in §13: Observe, Check, Spec, Test, Gate, Loop.
Phases 0 to 2 are planned in detail. Phases 3 to 6 are outlines and get planned
properly at the checkpoint before each one starts.

---

## 2. Status

Update this table at the end of every session. One line of status, no history; history
goes in the session log (section 9).

| Slice | What | Status |
|---|---|---|
| 0.1 | Land `remove-ai-assistant` | PR open, awaiting merge |
| 0.2 | Demolition | Not started |
| 0.3 | Fresh migration baseline | Not started |
| 0.4 | Harness: `make check`, hooks, stale docs | Not started |
| 1.1 | Canonical trace schema | Not started |
| 1.2 | Ingest API and service tokens | Not started |
| 1.3 | Retell reference mapping | Not started |
| 1.4 | Skill executions (n8n) | Not started |
| 1.5 | Component versions | Not started |
| 1.6 | CRM data per call (GoHighLevel) | Not started |
| 1.7 | Calls screen | Not started |
| 1.8 | MCP read surface | Not started |
| 2.1 | Check engine | Not started |
| 2.2 | First check library | Not started |
| 2.3 | Backfill and check results in the UI | Not started |
| 2.4 | Inbox v0 | Not started |
| M1 | Milestone 1 exit review | Not started |

**Next slice:** 0.2, once the 0.1 PR is merged.

---

## 3. What carries over from 1.x

This answers open question 6 in the vision. "Freeze" means leave it compiling and
tested but do not develop it until its phase arrives.

### Keep

| Area | Where | Role in 2.0 |
|---|---|---|
| Auth, users, companies (multitenancy) | `backend/app/api/deps.py`, `models/company.py`, `models/user.py` | Unchanged. |
| OAuth and the MCP adapter layering | `backend/app/api/routes/oauth.py`, `routes/mcp.py`, `mcp_server/` | The assistant's main door into the product. The layering stays; the tools are replaced. |
| Type chain | SQLModel, FastAPI, OpenAPI, Hey API codegen | Unchanged. |
| Integrations with encrypted keys | `models/integration.py`, `crud/integrations.py` | Holds the product's read access to providers (§5). |
| CI, release pipeline, Docker, Railway | `.github/`, `docs-internal/releases/` | Unchanged. |

### Freeze until Phase 4 (Test)

| Area | Where | Role in 2.0 |
|---|---|---|
| Eval runtime abstraction and Retell text runtime | `services/eval_runtimes/base.py`, `text/retell.py` | Already runs simulations on the provider's own engine, which is the provider strategy in §9. Becomes the first test connector. |
| Orchestrator, runs, results | `services/orchestrator.py`, `run_manager.py`, `models/run.py`, `models/test_case_result.py` | Test execution. |
| LLM judge, custom metrics, comparison | `services/judge.py`, `judge_metrics.py`, `comparison.py`, `models/custom_metric.py` | Tier 3 of verification (§7). Needs calibration added. |
| Test cases and eval configs | `models/test_case.py`, `models/eval_config.py` | Reshaped in Phase 4 to link to spec rules. |
| Custom endpoint runtime and agent contract | `eval_runtimes/text/custom_endpoint.py`, `models/agent_contract.py`, `docs/agents/contract.md`, `examples/` | The test connector for self-hosted frameworks (Pipecat and similar), where the team's deployed service is the engine (§9). The contract is text-only today; audio-level behaviour is vision open question 7. |

### Reshape

| Area | Problem today | Becomes |
|---|---|---|
| `Call` (`models/call.py`) | Retell-specific columns (`retell_call_id`, `retell_agent_id`), transcript plus an opaque `raw` blob. | The canonical trace: turns, tool calls with arguments and results, input variables, component versions, raw kept alongside. Slice 1.1. |
| Call sync (`api/routes/calls.py`, `services/retell.py`) | Retell fetch logic lives in a route file and writes rows directly. | A Retell reference mapping that emits canonical traces through the ingest path. Slice 1.3. |
| `AgentVersion` | A prompt-and-tools snapshot that the product owns and edits. | An observed fingerprint of what is live across flow, prompts, skills and settings. Slice 1.5, then verified state in Phase 5. |
| MCP tools | Four tools, all for listing agents and editing a prompt draft. | Read tools for calls and checks first (slice 1.8), then write tools for spec, tests and judges. |
| CLI (`backend/cli/`) | Drives the 1.x eval loop. | Undecided. See open question Q3. |

### Delete (slice 0.2)

Each of these is ruled out by a decided item in the vision.

| What | Where | Ruled out by |
|---|---|---|
| In-product AI assistant and prompt editor | Already removed on `remove-ai-assistant` | §4 No chat in the product |
| Prompt, tools and settings editors; publish and draft flow | `frontend/.../(agent)/_components/{prompt,tools,settings,header,diff}`, `agents/[agentId]/edit`, draft and publish routes in `routes/agents.py` | §15 the UI is for seeing and deciding |
| "Build from scratch" agents and the in-house agent simulator | `services/agent_simulator.py`, `eval_runtimes/text/connexity.py`, `tool_executor.py`, `tool_dispatch.py`, `agent_tool_definitions.py`, platform mode in `AgentMode` | §9 Connexity never re-implements an agent from a copy of its prompt |
| Deploying from the product | `services/webhook_deploy.py`, `deploy_retell_agent` in `services/retell.py`, deploy routes in `routes/environments.py`, `models/deployment.py`, `agents/[agentId]/deploy` | §5 and §16 the assistant deploys, the product has read access |
| Vapi and ElevenLabs import | `services/vapi.py`, `services/elevenlabs.py`, `provider_agent_import.py`, `models/imported_platform_config.py` | §9 the assistant writes provider mappings |
| Forms for creating tests, evals and metrics | `frontend/.../evals/create-eval`, `generate-test-cases-dialog.tsx`, manual test case panels in `observe/` | §15 creation happens through the assistant |
| Onboarding wizard | `frontend/apps/web/src/app/onboarding` | §13 onboarding starts in the assistant |

Keep the backend services behind the deleted forms where they are frozen for Phase 4
(test case generation, metric generation). Only the UI entry points go.

---

## 4. Phase 0: clear the ground

Goal: a smaller codebase that contains nothing the vision rules out, with a harness
that makes later sessions fast and safe.

### 0.1 Land `remove-ai-assistant`

- Run the full backend and frontend checks, regenerate the client, fix what breaks.
- Review the new migration `rm_ai_assistant_001_drop_prompt_editor.py`.
- Commit and open a PR to `main`.
- **Done when:** CI is green and the PR is merged.

### 0.2 Demolition

- Delete everything in the Delete table above. One PR per row or small group of rows,
  so each diff is reviewable.
- For each deletion: remove routes, CRUD, models, services, CLI commands, MCP tools,
  frontend screens, tests and public docs that mention it. Regenerate the client.
- Before deleting anything not named in the table, stop and ask.
- **Done when:** the checks pass, the app boots, and the agent screen shows only what
  survives (calls, and the frozen eval screens in read-only form).

### 0.3 Fresh migration baseline

- There are 64 Alembic revisions describing a schema that is about to change shape.
  Since no 1.x data is owed, squash to one baseline after demolition.
- `alembic check` currently reports a large pre-existing drift between the models and
  the migrated schema (enum column types, foreign key names, indexes, a `user.oauth_id`
  column the models no longer have). The baseline must end with `alembic check` clean.
- **Done when:** `alembic upgrade head` on an empty database produces the current
  models, `alembic check` reports no drift, and the test database bootstraps from the
  single baseline.

### 0.4 Harness

- Add `make check` that runs every gate in one command (ruff, format check, pyright,
  pytest, frontend lint, type check, client-is-fresh check).
- Fix the frontend type check in CI. `pnpm turbo check-types` runs zero tasks because
  no package defines a `check-types` script (the app's script is `typecheck`), so CI
  has never type-checked the frontend. Found in slice 0.1; `tsc --noEmit` passes today.
- Add the MCP server tests to CI. They pass locally (`uv run --extra dev pytest` in
  `mcp_server/`) but no workflow runs them.
- Make local test runs work out of the box. The root `.env` here points
  `DATABASE_URL` at a hosted database, and the local Postgres container rejects the
  password in `.env`, so slice 0.1 ran tests in a throwaway container.
- Add Claude Code hooks in `.claude/settings.json` (note: this file is gitignored
  today; decide whether to track it): block edits under
  `frontend/apps/web/src/client/`, and run the client generator reminder after route
  or model edits.
- Fix stale docs: `docs-internal/data-model.md` (still describes `EvalSet`),
  `CONTRIBUTING.md` (refers to a frontend `.env.example` that does not exist).
- Mark `README.md`, `CLI_README.md` and `docs/` as describing 1.x with a short banner.
  The full rewrite waits for the end of the rebuild.
- **Done when:** `make check` passes from a clean checkout.

---

## 5. Phase 1: Observe (ladder level 1)

Goal: every call of reference agent 1 appears as one joined trace, with the version of each
component that served it.

### 1.1 Canonical trace schema

Design session first, then models and migration.

- Required core (§9): call, turns, tool calls with arguments and results, input
  variables, component versions.
- Optional extensions: audio, timings, cost, provider-specific fields.
- Unmapped provider data is kept raw next to the mapped trace.
- Tool calls and turns become queryable rows or typed JSONB with indexes; decide in the
  design session based on what the checks in Phase 2 need to query.
- Write the schema as a public doc under `docs/`, because the assistant will write
  mappings against it.
- **Done when:** the schema doc is approved, the models and migration exist, and three
  hand-built example traces validate.

### 1.2 Ingest API and service tokens

- `POST` ingest endpoint that accepts a canonical trace plus raw payload.
- Service tokens for ingest. Today the product only has user JWT cookies and MCP OAuth;
  a provider webhook has neither.
- Conformance report on ingest: which capabilities this trace enables (for example
  "no tool results, so number provenance cannot run").
- Idempotent on provider call ID.
- **Done when:** an example trace can be posted with a service token, read back, and
  its conformance report lists the right capabilities.

### 1.3 Retell reference mapping

- Move Retell fetch logic out of `api/routes/calls.py` into a mapping module that turns
  Retell call payloads into canonical traces.
- Two triggers: Retell webhook, and scheduled pull for backfill and gaps.
- Capture tool call arguments and results, dynamic variables, and the Retell agent
  version that served the call.
- **Done when:** the last 30 days of reference agent 1 calls are ingested and a sample of
  ten matches the Retell dashboard turn for turn.

### 1.4 Skill executions (n8n)

- Read-only n8n connection registered as an integration.
- Link each tool call to the n8n execution it triggered, with node-by-node inputs and
  outputs (§8: agent, call, tool call, execution, node).
- The correlation method is a design question: see Q4.
- No workflow list, no standalone execution browser.
- **Done when:** for a real call, each backend tool call opens to its node-by-node
  execution.

### 1.5 Component versions

- Record, per call, the version of each component: Retell agent and flow version, the
  prompt hash, and each n8n workflow version.
- Store a fingerprint per observed state. "Verified" is added in Phase 5; for now every
  state is simply "observed".
- **Done when:** two calls served by different workflow versions show different
  fingerprints, and the call screen shows which is which.

### 1.6 CRM data per call (GoHighLevel)

- Read-only GoHighLevel connection.
- Per call: what came in before the call and what was written back after it.
- Fetched after a short delay because writes are asynchronous (§8).
- This slice can move after Phase 2 if it blocks the milestone.
- **Done when:** a real call shows its CRM record before and after.

### 1.7 Calls screen

- Replace the Observe drawer with a call screen: audio, transcript, each tool call
  expandable to its execution, CRM in and out, component versions.
- No editing, no forms.
- **Done when:** the "price dropped from 275 to 262" class of question (§2 item 4) can
  be answered from one screen without opening Retell, n8n or GoHighLevel.

### 1.8 MCP read surface

- Replace the four prompt tools with read tools: list calls, get a trace, get a tool
  call's execution, get component versions.
- Tools for the assistant to register connections with the product (§5).
- **Done when:** a Claude Code session in the reference agent's workspace can answer "what
  happened on call X" using only Connexity tools.

---

## 6. Phase 2: Check (ladder level 2)

Goal: deterministic checks run on every call and on history, and failures reach a human.

### 2.1 Check engine

- A check is a pure function from a canonical trace to a list of findings. Each finding
  points at exact turns or tool calls.
- No model calls in this tier.
- Registry, per-agent enablement and parameters, results stored per call and per check
  version.
- Runs on every ingest.
- **Done when:** a trivial check runs on ingest and its finding is stored against the
  right turn.

### 2.2 First check library

From §7 and the evidence in §2:

- **Number provenance:** every dollar figure the agent says traces to a tool result, an
  input variable, or something the caller said.
- **Value spoken on an empty result:** a price stated when the backend returned nothing
  or had not returned yet.
- Two questions in one turn.
- Stage directions spoken aloud.
- A reply written on the caller's behalf, or several turns collapsed into one.
- Hang-up directly after caller acceptance.
- **Done when:** each check has unit tests built from real traces, with both a failing
  and a passing example.

### 2.3 Backfill and check results in the UI

- Run all checks over ingested history.
- Show findings on the exact turns in the call screen, and a per-check summary per
  agent.
- **Done when:** the history of reference agent 1 is fully checked and browsable.

### 2.4 Inbox v0

The inbox is the home screen (§11, §15). Version 0 is deliberately small.

- One item type: failed check.
- Grouping: many calls failing the same check become one item.
- Actions: acknowledge, dismiss as false positive (which is recorded against the check),
  comment.
- No routing rules, dispatch modes or approval policy yet. Those are Phase 6.
- MCP tools so the assistant can list and read items.
- **Done when:** the inbox is the landing page and shows grouped check failures.

### Milestone 1 exit review

The milestone passes when the product would have caught what case study 1 (vision §2)
suffered:

1. Every reference agent 1 call from the last 30 days is a joined trace with versions.
2. Run over history, the checks flag the known incidents from §2: the invented 275
   price, the monologue with stage directions, the hang-up after a yes.
3. The false positive rate on a hand-reviewed sample of 50 calls is low enough that
   Dmytro would leave the checks switched on. He sets the number at review.
4. A fresh Claude Code session can diagnose a flagged call using only Connexity tools.

5. Nothing outside the mapping and connector modules names Retell, n8n or GoHighLevel.

After the review: retune `CLAUDE.md` and the lifecycle doc, then plan Phase 3 in detail.

---

## 7. Phases 3 to 6: outlines

These are placeholders. Each gets a planning session at its checkpoint, using what the
earlier phases taught.

### Phase 3: Spec (level 3)

- Rules in plain language with provenance: who decided, when, source message, exact
  words (§6).
- Enforcement placement per rule; money, safety and compliance rules flagged when only
  the prompt enforces them.
- Rule editing in the UI. Decision questions as an inbox item type.
- MCP: propose a rule with linked evidence; the user confirms.
- Checks from Phase 2 get linked to the rules they enforce.

### Phase 4: Test (level 4)

- Unfreeze the eval stack. Test cases link to spec rules; coverage and staleness views.
- Validation on submission: looping personas, stale mocks, ambiguous metrics.
- Judge calibration: agreement with human labels and stability across repeated runs;
  advisory until trusted.
- Classifier tier (Jev, §7). Needs a vendor evaluation first.
- Backend edge-case tests for skills, run by the product (vision open question 3).
- Harness integrity: shared state between tests, test traffic reaching production.

### Phase 5: Gate (level 5)

- Verified-state fingerprints. Polling live state and comparing.
- Bypass detection with the three cases in §5, partial deploy ranked highest.
- Versions timeline. Pre-deploy hook and standing instructions for the workspace.

### Phase 6: Loop (level 6)

- Full inbox: priority, routing rules, approval policy, snooze and digest.
- Dispatch modes: Manual, Investigate, Prepare (§11). Needs vision open question 1
  answered (where automatic sessions run).
- Incidents: severities, lifecycle, pre-approved containment (§12).
- Assistant-first onboarding: task playbooks with verify calls, the fire drill (§13).

### Cross-cutting, scheduled when their phase needs them

- Focus sharing, pins and navigate-back between product and assistant (§4).
- Client feedback intake through the assistant (§10).
- Generic provider mappings as saved artifacts for providers beyond Retell (§9).
- Public repositioning: README, docs site, website. Last.

---

## 8. Open questions

Questions that block a slice. The vision's own open questions (§18) are not repeated
unless a slice depends on them.

| # | Question | Blocks | Claude's recommendation |
|---|---|---|---|
| Q3 | What happens to `connexity-cli` on PyPI? | 0.2 | Freeze it with the eval stack and decide in Phase 4. The assistant uses MCP; CI may still want a CLI for the gate. |
| Q4 | How is a Retell tool call matched to its n8n execution? | 1.4 | Have the skill return its execution ID in the tool response. Fall back to matching on webhook time and payload for history. |
| Q5 | Where do real reference agent traces live for tests? They cannot go into a public repo. | 1.1 | A gitignored `fixtures-private/` directory plus a small set of hand-anonymised traces committed as test fixtures. |
| Q6 | Are deterministic checks a built-in library with per-agent parameters, or can the assistant author new ones through the API? | 2.1 | Built-in library for Milestone 1. Assistant-authored checks need a sandbox and belong with Phase 4. |
| Q7 | Do turns and tool calls become tables or typed JSONB? | 1.1 | Decide in the 1.1 design session from the queries Phase 2 needs. |

---

## 9. Decision log

Append only. One line each: date, decision, who decided. Claude records a decision as
Dmytro's only when he stated it in his own words.

| Date | Decision | By |
|---|---|---|
| 2026-10-06 | Rebuild in place in this repo. | Dmytro |
| 2026-10-06 | No compatibility owed to 1.x users, data or CLI. | Dmytro |
| 2026-10-06 | Development is Dmytro plus Claude Code. | Dmytro |
| 2026-10-06 | Milestone 1 is reference agent 1 (Retell + n8n + GoHighLevel) at Observe and Check. | Dmytro |
| 2026-10-06 | Keep the custom endpoint runtime and agent contract (frozen) as the connector for self-hosted frameworks such as Pipecat. Delete only the in-house simulator. | Dmytro, after raising Pipecat |
| 2026-10-06 | The vision doc may be committed. It must not name the client or their company; operational detail stays. | Dmytro |
| 2026-10-06 | Reference agent 1 is not the central piece. More examples on other stacks will be added. | Dmytro |

---

## 10. Session log

Append one entry per session: date, slice, what shipped, what was learned, what is
next. Keep each entry under ten lines.

### 2026-10-06: planning

- Read the vision, the 1.x codebase and the Claude context.
- Wrote this plan, the lifecycle doc, and a new `CLAUDE.md` split into root, backend
  and frontend files.
- No product code changed.
- Q1 and Q2 answered the same day (see decision log). Vision §9 reworded to "the
  agent's own engine"; the first build reframed as case study 1 of several.
- Next: slice 0.1.

### 2026-10-06: slice 0.1

- Branch `remove-ai-assistant` brought up to date with `main` and checked.
- Results: ruff and format clean; pyright 0 errors; backend tests 793 passed; CLI tests
  36 passed; MCP server tests 10 passed; frontend lint clean; `tsc --noEmit` clean;
  generated client already fresh.
- Migration `rm_ai_assistant_001`: applies from an empty database, downgrades and
  re-upgrades cleanly, and leaves no prompt-editor drift.
- Review found one bug, fixed with a test: the superuser seed crashed prestart when
  `FIRST_SUPERUSER_PASSWORD` was outside 6 to 40 characters.
- Learned: the CI frontend type check is a no-op; the schema has pre-existing drift;
  local test runs need a `DATABASE_URL` override. All three are recorded under 0.3 and
  0.4.
- Not done: no `next build` and no manual click-through of the UI.
- Next: merge the PR, then slice 0.2 (needs Q3 answered).
