# The assistant adds the agents to sync

- **Owner:** Dmytro
- **Slice:** Milestone 1, feature 7 of the roadmap: "Assistant helps choose agents to
  sync".
- **Design:** No UI change. The Agents page is feature 15.
- **MCP:** adds `add_agents(workspace_id, agents)`, which creates agents in the workspace
  linked to their Retell agents. `list_agents` shows them, with their Retell id.

## Goal

The assistant decides with the person which Retell agents belong in this workspace,
using its own access to Retell to see the agents and their calls. Then it adds them to
Connexity with one call, each linked to its Retell agent through the workspace's Retell
connection. Only agents added this way sync (feature 8).

Connexity does not list Retell's agents or count their calls for the assistant: "Assistant
will have its own access to retell we dont need to give him a link to retell, he just
needs to know how to create and link agents in connexity" (Dmytro, 2026-11-12).

## What exists today

- **An agent linked to Retell** (platform mode: the integration and Retell's agent id)
  can be created today, and the on-request call pull works for it.
- **The workspace's Retell connection** exists since feature 6 (`connect_voice_platform`).
- **`list_agents`** shows a workspace's agents: name, platform, Retell agent name, created.
- **Readiness step 3** ("Agents and calls synced") is not started until feature 10.

## Changes

### Backend

- **`POST /api/v1/mcp/workspaces/{workspace_id}/agents`**, in the standard answer.
  - **Input:** a list of up to 100 agents, each a Retell agent id and, optionally, a name
    (default: Retell's name).
  - **Check:** Connexity reads the connection's Retell agent list once and refuses ids
    that are not in that account. This is a read, so a typo cannot create an agent that
    will never sync.
  - **Result:** each valid agent is created in platform mode, linked to the connection.
    An id already in the workspace is left as it is. The answer lists what was added,
    what was already there and what was refused, and why.
  - **Who added it:** the person, recorded on each agent (`created_by`, which exists).
  - **Rules:** only agents added here are synced; Connexity reads from Retell and never
    changes the agent there.
  - **Next steps:** check with `list_agents`; syncing calls is not available yet
    (feature 8).
  - **Errors:** without a Retell connection, the next step is `connect_voice_platform`.
    If Retell cannot be reached to check the ids, nothing is added and the next step is
    to try again.
- **`list_agents`** gains each agent's Retell agent id, so the assistant can match its
  own Retell view to Connexity's.
- **Readiness step 3** shows "in progress" with "N agents added" once any is added;
  "done" stays with feature 10.
- **The agent de-duplication** (Retell lists an agent once per version) moves from the
  integrations route into the Retell service, so both use it.

### MCP server

- **The `add_agents` tool,** marked as changing something and not destructive. Its
  description says to use your own Retell access to find the agents, ask the person
  which belong to this client, then call it.
- **Guides:** a "Choosing agents" section:
  - one Retell account may hold several clients' agents;
  - recommend agents with recent calls, and skip tests and drafts;
  - always ask the person;
  - pass Retell's agent ids.
- **`get_readiness`'s next steps** name `add_agents` once Retell is connected.

## Decisions

Decided by Dmytro:

- The assistant uses its own access to Retell to see agents and calls; Connexity only
  needs to let it create and link agents (2026-11-12).
- The person decides with the assistant; only chosen agents sync into the workspace
  (roadmap entry).

Proposed by Claude:

- Check the ids against the connected Retell account before adding (one read).
- Adding does not start syncing; continuous sync is feature 8.
- Readiness step 3 becomes "in progress" once agents are added.
- `list_agents` shows the Retell agent id.

## Answered questions

Dmytro accepted the revised plan ("Accept, build", 2026-11-12):

1. No removing agents in this feature.
2. 1.x agents created by hand are left as they are.

## Done when

- `make check` passes. Backend tests (Retell mocked with `respx`) cover:
  - adding new agents, with Retell's name or a given one;
  - an id already in the workspace;
  - an id not in the account;
  - Retell unreachable (nothing added);
  - no connection;
  - who added it recorded;
  - an unreachable workspace;
  - `list_agents` showing the Retell id;
  - Readiness step 3 in progress.
- Played through on running servers through MCP, with Retell mocked.
- **Dmytro, on app.connexity.ai after merge**, with Retell connected: ask the assistant to
  pick the agents for this client using its own Retell access. It adds them, `list_agents`
  shows them, and Readiness step 3 shows "in progress".

## Out of scope

- Listing Retell's agents or counting their calls in Connexity.
- Syncing calls (feature 8), the first scan (feature 10), the Agents page (feature 15).
- Removing agents (question 1). Vapi and ElevenLabs agents: the tool says only Retell is
  supported for now.

## Risks

- **The check reads the whole Retell agent list** (paged, up to 50,000 agents). For very
  large accounts that is a few seconds per call.
- **An agent added under the wrong workspace** stays until removal exists (question 1).

## Outcome

### Deviations from the plan

- **Agents are created without a prompt or a 1.x draft version.** The 1.x "platform"
  agent wants a system prompt and model and makes a draft version; an observed agent has
  neither. Call sync only needs the platform, the connection and Retell's agent id, so
  `add_platform_agent` creates exactly that. Agents created this way pass the web
  `AgentPublic` model (checked).
- **The fields are named `platform_agent_id`, not `retell_agent_id`,** so the canonical
  shape does not name one provider.
- **A revoked stored key is told apart from an outage.** The play-through showed that
  `add_agents` with a key Retell no longer accepts would have said "could not be
  reached, try again" forever. It now says the stored key was refused, with a next step
  to reconnect through `connect_voice_platform`.
- **The account check reads Retell's whole agent list** on each call. It is not cached.

### Check results

`make check` on the final tree: see the table below.

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

New tests:

- `test_mcp_add_agents.py` (10, Retell mocked):
  - adding with Retell's name or a given one, linked to the connection, and who added it;
  - `list_agents` showing the Retell id;
  - Readiness step 3 "2 agents added";
  - already added, an unknown id and a repeated id;
  - no connection;
  - Retell failing four ways (error, malformed, not JSON, timeout), with nothing added;
  - a revoked stored key;
  - another workspace;
  - request validation: empty list, blank id, over 100.

  All pass with CI's placeholder encryption key too.
- MCP server: the tool and its arguments (21 tests).

**Played through on running servers** (backend on port 8001, MCP server on port 8012),
connected like Claude Code through the real OAuth flow:

| # | Step | Came back |
|---|---|---|
| 1 | List tools | `add_agents`, `connect_voice_platform`, `create_workspace`, `get_readiness`, `list_agents`, `list_workspaces` |
| 2 | `add_agents` without a Retell connection | Error "This workspace has no Retell connection." with `connect_voice_platform` as the next step |
| 3 | `get_readiness` with a Retell connection | The next step names `add_agents` |
| 4 | `add_agents` with a stale stored key, checked against the real Retell API | Error "Retell refused the key stored for this workspace." with the reconnect step |
| 5 | `list_agents` afterwards | 0 agents: nothing added |

The success path against a real Retell account is covered by the mocked tests and is
Dmytro's test on app.connexity.ai.

`/code-review` (high) raised two findings, both not fixed:

- **Step 3 spins.** Once agents are added, Readiness step 3 is "in progress", which the
  screen shows with a spinner, though nothing syncs until feature 8. Dmytro decided to
  keep it ("Keep it").
- **Concurrent adds can duplicate an agent.** Two calls adding the same Retell agent at
  the same moment can both insert, because nothing in the database prevents it. A unique
  index needs a migration that checks for existing duplicates first; left for the sync
  feature.

**For Dmytro, on app.connexity.ai after merge**, with Retell connected: ask the assistant
to pick this client's agents from your Retell account (using its own Retell access) and
add them. They appear in `list_agents` with their Retell ids, and Readiness step 3 says
"N agents added".

### Not done

- **Syncing their calls** (feature 8) and the first scan (feature 10).
- **Removing an agent** (answered: later).
- **A unique constraint on one agent per Retell agent per workspace** (see above).
- **Throwaway data in the local dev database:** one play-through user, its OAuth client
  and a stale test Retell integration.
