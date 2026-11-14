# Agents page

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Agents page (no score or issues)" (10.111,
  moved into the Demo milestone by Dmytro on 2026-11-14).
- **Design:** `designs/screens/Connexity Agents.dc.html` (the list), prompt
  `designs/02-agents.md` (list part only). The screen wins where they differ, minus what
  the roadmap leaves out.
- **MCP:** `list_agents` gains what the page shows: platform and type, and calls in the
  period. No new tool.

## Goal

A person opens **Agents** in the sidebar and sees the workspace's agents at a glance:
each one's name, its platform and type, and how many calls it took in the period.

From the roadmap: "The Agents list: name, platform and type, calls. No latency (moved to
Milestone 2), no score, issues or agent profile; clicking a row does nothing."

## What exists today

- **No Agents page.** The sidebar has Calls and Issues.
- **The web API's agent list** (`GET /agents`) is the 1.x shape: drafts, published
  versions and eval summaries. Nothing on it is what this page needs.
- **`list_agents` (MCP)** lists agents with their spec state once #200 merges. It has no
  type or calls.
- **Each agent's type** can be read from the catalogue. The current version's
  instructions are either a single prompt or a conversational flow
  (`component_version` kinds `prompt` and `flow`).
- **When calls were last pulled:** each Retell account's last pull time is stored
  (`call_pull_account.last_pulled_at`, 10.009).

## Changes

### Backend

**`GET /agents/list`** (a new route, so the 1.x `GET /agents` stays untouched):

- **Rows:** the open workspace's linked agents, one per agent. Each has:
  - its name;
  - the platform ("Retell");
  - the type ("Single prompt" or "Conversational flow"), from its current version in
    the catalogue, or none when not known yet;
  - calls in the period.
- **The period:** last 7, 30 or 90 days, default 30, as on the Calls page.
- **The order:** most calls first, then by name (question 1).
- **"Synced":** when calls were last pulled for the workspace's Retell accounts, for the
  caption "Retell · synced 5 minutes ago".

**`list_agents` (MCP)** gains `type` and `calls` (in the last 30 days, or the `period`
passed). Its rules say what the numbers cover.

### Frontend

- **Agents in the sidebar,** in its decided place: Calls, Issues and Agents, in the
  order Home, Incidents, Action items, Agents, Calls, Roadmap, Issues, Settings. So
  Agents comes before Calls.
- **The Agents screen, as the export shows it, without what the roadmap leaves out
  (rule 14):**
  - the page bar: "Agents", the muted "Retell · synced 5 minutes ago", and the period
    picker;
  - one table: **Agent** (name, with "Retell · Conversational flow" muted underneath)
    and **Calls**;
  - no Score, Critical issues or Latency columns;
  - **rows open nothing,** and have no hover state, until the agent page (10.112).
- **"No spec" label** (question 2).
- **Empty state:** "No agents yet. Your assistant adds them during setup." (question
  3).

### Docs

- `docs-internal/mcp-architecture.md`: `list_agents` gains `period`.

## Decisions

Decided by Dmytro:

- **The roadmap's scope:** name, platform and type, calls; no latency, score, issues or
  profile; rows do nothing (roadmap entry).
- **The sidebar order** (2026-11-12).
- **The Agents page comes before Clarifications in the Demo milestone** (2026-11-14,
  through the roadmap).

Proposed by Claude:

- **A new route** rather than reshaping the 1.x one, which the frozen eval screens'
  types still lean on. It is deleted when those go.
- **The type comes from the catalogue,** so it costs no call to Retell.
- **"Synced" uses the latest pull** across the workspace's Retell accounts.

## Questions

1. **The order.** The design sorts worst first by score, and there is no score yet.
   Recommended: most calls first, then by name. The alternative is by name.
2. **"No spec" next to an agent's name** (design item 13). It works once #200 merges:
   specs exist and `list_agents` already knows each agent's state. Recommended: show
   it, since it is real and nudges the setup along. The alternative is to wait for the
   Spec tab. This pull request would then follow #200.
3. **The empty state's words.** Recommended: "No agents yet. Your assistant adds them
   during setup." The design has no empty state, so this line is new; say if you would
   rather design it first.

## Done when

- `make check` passes. Backend tests cover:
  - rows for linked agents only, in the open workspace;
  - the type from the catalogue, and none when it is not known;
  - calls per period;
  - the order;
  - "synced" from the latest pull;
  - `list_agents` with `type`, `calls` and `period`;
  - another workspace.
- Played through on a running backend through the API and MCP.
- **For Dmytro to check on screen** (after merge, the demo workspace):
  - Agents is in the sidebar before Calls;
  - the table shows the demo agent with "Retell · …" and its calls;
  - the caption says when calls were last synced;
  - the period picker changes the calls;
  - rows do not open;
  - dark and light.

## Out of scope

- **The agent page,** clickable rows and latency (10.112).
- **Score, critical issues and latency** (later milestones).
- **The Spec tab** (after the demo).
- **Removing the 1.x `GET /agents` and its types:** they go with the frozen eval stack.

## Risks

- **The type can be unknown** for an agent whose version Connexity has not read yet.
  The row then shows only "Retell".
- **"Synced" covers the scheduled pull only.** Calls that arrive by webhook do not move
  it.

## Outcome

### Deviations from the plan

- **Built after #200 merged** (Spec part 2), as question 2 required. "No spec" shows
  for an agent with no spec at all. An adopted spec waiting for review does not show a
  label; the design has none for it.
- **The type comes from the agent version's own catalogue row,** which links to its
  prompt or flow, in one query for every agent. It does not read each prompt. Found by
  `/code-review`.
- **The route is `/agents/list`,** included before the 1.x agents router, whose
  `/agents/{agent_id}` would otherwise catch it. A comment and the tests guard the
  order.
- **The decision log** gains 10.11 closing after its API and MCP parts, and the Spec tab
  moving after the demo. The status table marks Spec part 2 Done (#200).

### Check results

`make check` on the final tree. `pnpm build` also succeeds, with `/agents` among the
routes.

| Step | Result |
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

**New tests in `test_agents_list.py` (5):**

- linked agents only;
- the type: single prompt, conversational flow, and none when not read yet;
- calls per period;
- most calls first, then by name;
- "synced" from the workspace's own Retell account only;
- the spec state on the list;
- another workspace, not signed in, and an unknown period;
- `list_agents` with `type`, `calls` and `period`.

**Played through on a running backend** (port 8027, local database). The throwaway
workspace had three agents, a prompt, a flow and one never read, and a Retell account
pulled 3 minutes earlier.

| # | Request | Came back |
|---|---|---|
| 1 | `GET /agents/list` | 200; front desk single prompt 3 calls, flow line conversational flow 1, quiet line no type 0; all "none" for spec; synced set |
| 2 | `period=7d` | Calls 2, 1, 0 |
| 3 | Not signed in | 401 |
| 4 | `period=1y` | 422 |
| 5 | MCP `list_agents` | The same types and calls, newest first |

The backend log had no errors. The throwaway data was deleted afterwards.

**`/code-review` (high) raised four findings:**

- **Fixed:** types read with two queries per agent.
- **Fixed:** current versions computed twice.
- **Fixed:** a type ignore on the period.
- **Not changed:** the route depends on the routers' order. The tests catch a change.

**For Dmytro to check on screen** (app.connexity.ai after merge, the demo workspace):

1. **Agents** is in the sidebar before Calls, with the robot icon.
2. **The page bar:** "Agents" and "Retell · synced N minutes ago" (once the scheduled
   pull has run for the account), and the period picker.
3. **The table:** the demo agent, with "Retell · Single prompt" or "Conversational flow"
   underneath, and its calls in the last 30 days. A "No spec" label shows until the
   assistant writes one.
4. **The period picker** changes the calls.
5. **Rows do not open,** with no hover.
6. **No Score, Critical issues or Latency columns.**
7. **Dark and light.**

### Not done

- **The agent page, clickable rows and latency** (10.112).
- **Score and critical issues** (later milestones).
- **The screens were not looked at by the session.**
