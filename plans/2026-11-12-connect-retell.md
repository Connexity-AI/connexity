# Connect Retell through the assistant

- **Owner:** Dmytro
- **Slice:** Milestone 1, feature 6 of the roadmap: "Connect Retell through the
  assistant".
- **Design:** No UI change. There is no connection form in the app (Decided
  2026-11-09); Readiness step 2 already shows the platform once connected.
- **MCP:** adds `connect_voice_platform(workspace_id, platform, api_key)`.
  `get_readiness`'s next steps name it.

## Goal

The person gives their assistant the Retell API key. The assistant registers the
connection in the right workspace through MCP; Connexity checks the key against Retell
and stores it encrypted. Readiness step 2 then ticks with "Retell".

## What exists today

- **Integrations:** a workspace's provider connections, with the key encrypted (Fernet)
  and a masked copy for display. Each provider has a connection check:
  - Retell lists one agent with the key;
  - Vapi and ElevenLabs have their own checks;
  - n8n needs an address too.
- **`POST /api/v1/integrations/`** creates one for the open web workspace after the
  check. No screen uses it since M1.1, and MCP has nothing.
- **Readiness step 2** is done when the workspace has a voice platform integration
  (M1.4).
- **Nothing records who created an integration.**

## Changes

### Backend

- **`POST /api/v1/mcp/workspaces/{workspace_id}/connections`**, in the standard answer.
  It takes the platform (Retell, Vapi or ElevenLabs) and the API key, checks the key
  with the platform, and stores it.
  - **A refused key** answers with the platform's reason and a next step ("Check the key
    in Retell's dashboard under API keys, then call again").
  - **A workspace that already has that platform** gets its key replaced (rotation), not
    a second connection (question 1).
  - **The answer** has the platform, the masked key and when it was connected, never
    the key. The rules say the key is stored encrypted and that Connexity only reads
    from the platform. The next steps say what comes next (choosing agents to sync,
    feature 7).
- **Who connected it:** the integration records the person and the assistant (the OAuth
  client's name) that connected it. It shows in the answer, and later in Settings and
  the audit log.
- **The connection check moves** from the integrations route into a small service, so
  the web route and the MCP route share it.

### MCP server

- **The `connect_voice_platform` tool,** marked as changing something but not
  destructive. Its description tells the assistant to ask the person for the key, never
  to echo it back, and to name the workspace.
- **`get_readiness`'s next step for step 2** names the tool.
- **Guides:** the Readiness guide's step 2 and a short "Voice platforms" section in the
  Connect guide: where Retell's key is, and that Connexity never writes to Retell.

## Decisions

Decided earlier, applied here:

- The assistant registers connections through MCP; there is no connection form in the
  app (2026-11-09, roadmap entry).
- Connexity only reads from providers; it never deploys or writes to them (ground
  rules).
- Every feature ships its MCP tools, few and shaped around the work (rule 10).

Proposed by Claude:

- One tool for all voice platforms Connexity already checks (Retell, Vapi, ElevenLabs).
  Only Retell is tested against the real service here.
- One connection per platform per workspace: connecting again replaces the key.
- Record the person and the assistant that connected it.
- The key passes through the assistant's session. That is the cost of having no form in
  the app; Connexity never returns it.

## Answered questions

Dmytro accepted the recommendations ("Accept, build", 2026-11-12):

1. One connection per platform per workspace; connecting again replaces the key.
2. No disconnect tool now; Disconnect comes with Settings.

No Retell key was given for local testing, so the real Retell check is Dmytro's test on
app.connexity.ai.

## Done when

- `make check` passes. Backend tests cover:
  - connecting with a key Retell accepts (mocked);
  - a refused key, with a timeout and an empty or malformed answer from Retell
    (`respx`);
  - replacing the key on a second connect;
  - the key never in an answer;
  - who connected it recorded;
  - an unreachable workspace;
  - Readiness step 2 done afterwards.
- Played through on running servers with a real assistant session (the MCP Python
  client): `connect_voice_platform` with a wrong key is refused with the next step.
  With a real Retell key, if Dmytro provides one for local testing, Readiness shows
  "Retell".
- **Dmytro, on app.connexity.ai after merge:** ask Claude Code or ChatGPT to connect
  Retell, give it the key, and see Readiness step 2 tick with "Retell".

## Out of scope

- Choosing which agents to sync (feature 7), syncing (feature 8), the Retell webhook.
- Disconnect, Settings › Connections, the audit log.
- n8n and CRM connections (backends, Milestone 8).

## Risks

- **The key sits in the assistant's conversation.** The person pastes it into Claude or
  ChatGPT, so it is stored wherever that conversation is. The tool description tells
  the assistant not to repeat it; the person may still prefer a restricted key.
- **Replacing a key silently** could point a workspace at a different Retell account.
  The answer says when a key was replaced, so the assistant can tell the person.

## Outcome

### Deviations from the plan

- **An unreachable Retell is not a refused key.** Retell answering 401 or 403 means
  refused (400, with where to find the key). A timeout, connection failure or any other
  status means Retell could not be reached (503, "try again in a minute; nothing was
  stored"). This needed a new check, `retell_key_status`; Vapi and ElevenLabs keep their
  yes-or-no checks (from `/code-review`).
- **The web route records who created an integration too** (from `/code-review`), so
  connections made through `POST /integrations` are not anonymous.
- **A blank key, or one of only spaces,** is refused as invalid (422) before Retell is
  asked.
- **Which assistant made the call** is now available to every MCP route
  (`McpAssistantName`), read from the token's client.
- **Existing tests that patched the connection checks** now patch them where they moved
  (`app.services.connections`). Nothing they check changed.

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

- `test_mcp_connections.py` (Retell mocked with `respx`):
  - a key Retell accepts: stored encrypted, who connected it recorded, the key never in
    the answer, Readiness step 2 done;
  - connecting again replaces the key and says so;
  - a refused key;
  - Retell failing: server error, timeout, unreachable, and an empty 200;
  - another workspace is not found and Retell is never asked;
  - an unknown platform or a blank key.
- `test_integrations.py`: the web route records who created it.
- MCP server: the tool, its hints and its arguments (20 tests).

Migration `0012_integration_created_by` applies, reverses and re-applies on the local
database, with no drift.

**Played through on running servers** (backend on port 8001, MCP server on port 8012),
connected like Claude Code through the real OAuth flow:

| # | Step | Came back |
|---|---|---|
| 1 | `get_readiness` before connecting | The next step names `connect_voice_platform` |
| 2 | `connect_voice_platform` with a made-up key, checked against the real Retell API | Tool error "Retell refused this API key." with the next step pointing to Retell's API Keys; the key not echoed |
| 3 | `get_readiness` after the refusal | Step 2 still not started |

A real key was not used: none was provided for local testing. The accepted path is
covered by the mocked tests and is Dmytro's test on app.connexity.ai.

`/code-review` (high) raised three findings, all fixed (listed under deviations).

**For Dmytro, on app.connexity.ai after merge:** in Claude Code or ChatGPT, ask it to
connect Retell to your workspace and give it a Retell API key. It should say Retell is
connected without repeating the key, and Readiness step 2 should show "Retell". Try a
wrong key once to see the refusal.

### Not done

- **Not tested with a real Retell key.**
- **Disconnect** (answered: later, with Settings).
- **Choosing agents to sync** (feature 7) and **syncing** (feature 8).
- **Throwaway data in the local dev database:** one play-through user and its OAuth
  client.
