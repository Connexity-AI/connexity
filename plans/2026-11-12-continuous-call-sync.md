# Continuous call sync: the Retell webhook, set up by the assistant

- **Owner:** Dmytro
- **Slice:** Milestone 1, feature 8 of the roadmap: "Continuous call sync". It also
  carries feature 9's recommendation, "Research: efficient call ingestion" (question 1).
- **Design:** No UI change.
- **MCP:** no new tool. `add_agents` and `get_readiness` give the webhook address and
  the step to set it in Retell. `get_readiness` says whether the webhook is working.

## Goal

Every call of an added agent reaches Connexity on its own, seconds after it ends,
whether or not anyone has the app open. The Retell webhook does it. Setting the webhook
in Retell is a setup step the assistant does with its own Retell access; Connexity gives
the address and shows when calls start arriving.

"We dont need anything beyond retell webhook right now its part of setup" (Dmytro,
2026-11-12). No scheduled pull, no scheduler job.

## What exists today

- **The Retell webhook** (`POST /api/v1/webhooks/retell/{integration_id}`):
  - It is verified with the connection's key.
  - It stores a finished call (`call_ended`, `call_analyzed`) of an added agent, maps it
    to a trace, resolves its versions and checks it.
  - Storing is idempotent: the second event for the same call replaces the first.
  - A call of an agent that was not added is acknowledged and ignored.
- **Nothing tells the assistant the webhook address,** and nothing shows whether the
  webhook was set.
- **The on-request pull** (`sync_agent_calls`) stays for the first scan (feature 10),
  which brings an agent's history in.

## Changes

### Backend

- **The webhook address** of a Retell connection:
  `<backend public address>/api/v1/webhooks/retell/<connection id>`. Built from
  `OAUTH_ISSUER_URL`, the backend's public address.
- **Each agent records when its last call arrived by webhook.** Readiness and the
  assistant can then tell "set up and working" from "not set up yet" (an agent with
  calls in Retell but none by webhook).
- **Review fixes to the webhook,** each with a test:
  - a call of an agent added to two workspaces from the same Retell account is stored in
    each (today only the first match is used);
  - a webhook for a connection whose key was replaced still verifies with the new key;
  - the webhook answers quickly and never 500s on a call it cannot map.

### Readiness and MCP

- **`add_agents`'s answer** gives the webhook address and, as next steps:
  1. set it as each added agent's webhook in Retell (with your own Retell access);
  2. then call `get_readiness` after the next call.
- **Readiness step 3** ("Agents and calls synced"):
  - **in progress**, with "N agents · M calls";
  - its next steps name the agents with no call by webhook yet, and repeat the address.

  "Done" stays with feature 10.
- **The Connect guide** gains a "Webhook" section: where the setting is in Retell (per
  agent, or for the whole account), that only added agents' calls are stored, and that
  calls before the webhook was set come in with the first scan.

### Feature 9's recommendation

`docs-internal/call-ingestion.md`, short:

- **Now:** the Retell webhook, set up by the assistant, is the only continuous path.
- **History:** the first scan (feature 10) pulls an agent's past calls on request.
- **Later, if needed:** a scheduled pull as a safety net for calls the webhook missed
  (a deploy, an outage, an agent whose webhook was never set), woken by Cloud Scheduler
  because Cloud Run scales to zero. Not built, by decision.

## Decisions

Decided by Dmytro:

- The Retell webhook is the only continuous path for now, and setting it is part of
  setup (2026-11-12).
- Calls sync continuously because alerts depend on it (2026-11-12).
- Connexity never writes to Retell (ground rules): the assistant sets the webhook.

Proposed by Claude:

- The webhook address is built from `OAUTH_ISSUER_URL`.
- Each agent records when its last webhook call arrived, to show whether setup worked.
- The three webhook fixes above.

## Answered questions

Dmytro accepted the recommendations ("Accept, build", 2026-11-12):

1. `docs-internal/call-ingestion.md` in this pull request is feature 9's deliverable;
   both roadmap rows close with it.
2. Calls missed during a deploy or outage are accepted for now.

## Done when

- `make check` passes. Backend tests cover:
  - the webhook address in `add_agents` and `get_readiness`;
  - a webhook call recorded on the agent;
  - the same Retell agent in two workspaces, stored in each;
  - a replaced key verifies;
  - an unmappable call answers 200 "ignored";
  - Readiness step 3's counts and next steps.
- Played through on running servers: sign a Retell-shaped webhook with the connection's
  key and post it. The call is stored, the agent's last webhook moves, and
  `get_readiness` counts it.
- **Dmytro, on app.connexity.ai after merge:** the assistant adds an agent, sets the
  webhook in Retell from the address Connexity gives, you make a test call, and it
  appears within seconds with Readiness counting it.

## Out of scope

- A scheduled pull, Cloud Scheduler, a backfill (Decided: not now).
- Pulling an agent's history (feature 10), live updates (feature 14).
- Vapi and ElevenLabs webhooks.

## Risks

- **Calls during a deploy or outage are lost** if Retell's retries run out (question 2).
- **Work after the webhook answers** (finding the n8n executions of a call) runs as a
  background task. On Cloud Run that may be slowed once the answer is sent, because CPU
  is given mainly during requests. It is not new; noted for the deploy settings.
- **An agent whose webhook is never set** gets no calls. Readiness names it.

## Outcome

### Deviations from the plan

- **The webhook stores the call in every workspace that added the same Retell agent from
  the same account.** It finds those workspaces by the key their Retell connections
  hold. The answer gains `call_ids`; the existing test that checks the exact answer now
  expects that field too. Nothing it checks was loosened.
- **The "no call by webhook yet" next step** counts only Retell agents, and builds the
  address from that agent's own connection (from `/code-review`).
- **The key match catches only the bad-key error** (`InvalidToken`), not every error
  (from `/code-review`, `backend/CLAUDE.md`).
- **The replaced-key and unmappable-call fixes** needed no code change. The webhook
  already read the connection's current key and answered "ignored" on a call it could
  not map. Both now have tests.

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

- `test_webhooks.py`:
  - a stored call records when the webhook last brought one;
  - the same Retell agent in two workspaces with the same key gets the call in both,
    and an agent under another account's key does not;
  - a replaced key verifies and the old one does not.
- `test_mcp_add_agents.py`:
  - the webhook address in `add_agents`'s next steps;
  - Readiness step 3 "2 agents · 0 calls";
  - `get_readiness` naming the agents with no webhook call yet, with the address.
- Every test that stores a key passes with CI's placeholder encryption key.

Migration `0013_agent_last_webhook_call` applies, reverses and re-applies on the local
database, with no drift.

**Played through on the running backend** (port 8001). A throwaway workspace, a test
Retell connection with a made-up key, one added agent, and invented Retell payloads signed
with that key:

| # | Step | Came back |
|---|---|---|
| 1 | Readiness after adding the agent | Step 3 "in progress · 1 agent · 0 calls" |
| 2 | Signed `call_ended` | 200 "stored", 1 call |
| 3 | `call_analyzed` for the same call | 200 "stored" (the same call, replaced) |
| 4 | A wrong signature | 401 |
| 5 | The agent's last webhook call | Recorded |
| 6 | Readiness again | Step 3 "in progress · 1 agent · 1 call" |

The backend log had no errors.

`/code-review` (high) raised five findings. Fixed: the bare exception, and the webhook
step naming non-Retell agents. Not fixed:

- **Each webhook call decrypts every Retell connection** to find others with the same
  key. That is fine at today's scale. At thousands of workspaces it needs a stored
  fingerprint of the key to look up instead.
- **The webhook reads Retell's versions once per workspace copy** of an agent before
  answering. That is rare (one agent in several workspaces) and bounded by Retell's
  10-second limit, with Retell retrying if it is passed.
- **The webhook address falls back to `http://localhost:8000`** when `OAUTH_ISSUER_URL`
  is unset. The hosted backend sets it (`docs-internal/deployment.md`).

**For Dmytro, on app.connexity.ai after merge**, with Retell connected and an agent
added:

1. Ask the assistant to set the webhook in Retell from the address `add_agents` or
   `get_readiness` gives.
2. Make a test call to that agent.
3. Within seconds, Readiness step 3 counts it, and `get_readiness` no longer names that
   agent as waiting.

### Not done

- **A safety-net pull and Cloud Scheduler** (by decision; described in
  `docs-internal/call-ingestion.md` for later).
- **Past calls** come with the first scan (feature 10).
- **Not tested with a real Retell webhook.**
- **Throwaway data in the local dev database:** one play-through user, its test Retell
  connection and agent, and one invented call.
