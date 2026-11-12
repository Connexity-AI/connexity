# Readiness: the screen a new workspace opens on

- **Owner:** Dmytro
- **Slice:** Milestone 1, feature 4 of the roadmap: "Readiness and onboarding screen".
- **Design:** `designs/screens/Connexity Onboarding.dc.html` (the Readiness screen, from
  `12-adjustments.md` items 11 and 19), in the 2026-11-12 export already in the repo.
  Its sidebar is `Connexity Sidebar.dc.html`.
- **MCP:** adds `get_readiness(workspace_id)`: the steps, which are done, and what to do
  next. The assistant drives Readiness, so it must see it.

## Goal

A workspace that has not finished its first scan opens on Readiness: the screen that
says what is set up and what is not. It shows only the four Getting started steps:

1. Assistant connected.
2. Voice platform connected.
3. Agents and calls synced.
4. First scan done.

The seven controls come in later milestones. When no assistant is connected, step 1
shows the copyable command that connects Claude Code. The assistant reads the same steps
through MCP, so it knows what to do next.

## What exists today

- **Step 1 can be measured.** Assistant connections are OAuth grants per person. A
  person has an assistant connected while they hold a refresh token that is neither
  revoked nor expired, and the client that holds it has a name ("Claude").
- **Step 2 can be measured.** A workspace has a voice platform when it has a Retell
  integration.
- **Steps 3 and 4 have no definition yet.** "First scan: everything in the database"
  (feature 10) defines them and ticks them. Until then they are not done, which is true.
- The MCP server's public address is the backend's `OAUTH_DEFAULT_RESOURCE_URL`; the
  connect command needs it.
- `/` is the empty shell (M1.1).

## Changes

### Backend

- **A Readiness service** answers, for one workspace, the four steps, each with:
  - its state: done, in progress or not started;
  - a short detail ("Claude Code", "Retell");
  - for step 1 when not done, the connect command built from the MCP address.

  The checks:
  - **Step 1** is done when any member of the workspace has an assistant connected.
  - **Step 2** is done when the workspace has a Retell integration.
  - **Steps 3 and 4** are not started until feature 10 gives them a check.
- **`GET /api/v1/readiness`** for the open workspace (web).
- **`GET /api/v1/mcp/workspaces/{workspace_id}/readiness`** in the standard answer, with
  next steps that name only tools that exist today. For example, step 2 says to ask the
  person for their Retell key and that a connection tool comes with feature 6, rather
  than naming a tool that does not exist.

### Screen (from `Connexity Onboarding.dc.html`)

- `/` shows Readiness while the first scan is not done, which in this change is always.
- The page bar has "Readiness" and the percentage, then a thin progress bar and "x of y
  steps" (question 1).
- **The Getting started card:** one row per step, with its icon (done, in progress, not
  started), name and detail.
  - When step 1 is not done, its row opens with "Connect your AI assistant to Connexity.
    In Claude Code, run:" and the command with a **Copy** button that changes to
    "Copied".
  - The design's line under the card, "Your assistant is doing this. You can close this
    page.", is hidden for now (see Outcome).
- **Not shown, because nothing behind them works yet (rule 14):**
  - the Controls card;
  - the "Using another assistant?" link (question 3);
  - the spinner's progress bar and the live updates (feature 14);
  - "Open Home" (question 4).

### MCP

- `get_readiness(workspace_id)` in the adapter, its guide ("Readiness", served at
  `connexity://guides/readiness`), and the connect instructions mention it.

## Decisions

Decided earlier, applied here:

- Readiness is one list; onboarding is its first part. Before the first scan it is the
  whole screen, and the app opens on it after sign-up (`12-adjustments.md` item 19).
- Only the four Getting started steps in Milestone 1 (roadmap entry).
- Step 1 is the only place with a setup instruction for the person (design).

Proposed by Claude:

- Step 1 counts any member's connected assistant, since connections are per person and
  reach the workspaces that person can reach.
- Steps 1 and 2 are measured now, from what exists; features 5 and 6 then only need to
  make connecting work, and the steps tick on their own.
- The screen reads Readiness when it loads; ticking live is feature 14.
- `get_readiness` as the MCP tool, with a Readiness guide.

## Answered questions

Dmytro accepted the recommendations ("Accept, build", 2026-11-12):

1. The percentage counts the steps on screen: "1 of 4 steps", 25%.
2. Steps 1 and 2 are measured now.
3. "Using another assistant?" stays out until ChatGPT works (feature 5).
4. Where the app goes after the first scan is decided with feature 10.

## Done when

- `make check` passes. Backend tests cover each step's check, including:
  - a revoked or expired grant is not "connected";
  - another workspace's integration does not count;
  - the web route and the MCP route;
  - an unreachable workspace.
- Played through the API: a new workspace shows nothing done. After an OAuth connection
  step 1 is done; after adding a Retell integration through the existing API, step 2 is
  done. MCP `get_readiness` says the same.
- Dmytro, on screen:
  1. sign up and land on Readiness with step 1 open and the connect command;
  2. Copy changes to Copied;
  3. connect Claude Code with the command, reload, and step 1 is done with "Claude Code"
     and the "Your assistant is doing this" line.

## Out of scope

- The seven controls, the Readiness ring in the sidebar and the stripe at the top (later
  milestones).
- Live updates (feature 14), connecting Retell (feature 6), the first scan (feature 10).

## Risks

- **Step 1 can be done while the assistant is not usable,** for example a grant made on
  another deployment's MCP address. The check counts grants, not working calls.
- **The connect command shows whatever MCP address is configured.** If
  `OAUTH_DEFAULT_RESOURCE_URL` is unset, step 1 has no command to show. The screen then
  says the MCP address is not configured, rather than showing a wrong command.

## Outcome

### Deviations from the plan

- **Step 2 counts any voice platform Connexity syncs** (Retell, Vapi, ElevenLabs), not
  only Retell, so the step does not name the first example. The detail shows which one;
  n8n does not count.
- **Step 1 counts a connection without a refresh token too.** The play-through found that
  a client registered without the refresh grant left step 1 "not started" after
  connecting. An assistant now counts as connected while it holds:
  - a refresh token that is neither revoked nor expired, or
  - an access token that has not expired (its code was exchanged within the access
    token's lifetime, 60 minutes).

  Claude asks for refresh tokens, so it stays connected.
- **The page is wrapped in `ErrorBoundarySuspense`** (from `/code-review`) with an empty
  fallback: the design has no loading state, and the skeleton primitive was deleted in
  M1.1.
- **A failed Copy selects the command** so it can be copied by hand (an insecure origin
  has no clipboard). There is no new text.
- **When the MCP address is not configured**, step 1 says so in one line instead of
  showing a command. This copy is not in the design; it is an error state.

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

`next build` passes; every class the screen uses is in the built CSS.

New tests:

- `test_readiness.py` (11): a new workspace, a connected assistant, a revoked or expired
  refresh token, a connection without a refresh token (inside and outside the access
  token's hour), a voice platform but not n8n, another workspace not counting, no MCP
  address, MCP in the standard shape, an unreachable workspace, and next steps once the
  platform is connected.
- MCP server tests: 18, including `get_readiness` and the tool list.

**Played through on running servers** (backend on port 8001, MCP server on port 8012), once
with a client that asks for refresh tokens and once without:

| # | Step | Came back (both runs) |
|---|---|---|
| 1 | New workspace | 0 of 4, 0%; all not started; the command `claude mcp add --transport http connexity http://localhost:8012/mcp` |
| 2 | Connect "Claude Code" through the real OAuth flow (sign in, Allow) | 1 of 4, 25%; step 1 done, "Claude Code"; no command |
| 3 | A Retell integration in the workspace* | 2 of 4, 50%; step 2 done, "Retell" |
| 4 | MCP `get_readiness` | 2 of 4; 2 next steps; guide `connexity://guides/readiness`; the connect instructions mention `get_readiness` |
| 5 | Read the Readiness guide | "# Readiness" |

\* Written straight to the local database, because creating an integration through the
API checks the key against Retell.

The first run of row 2 found the refresh-token gap above. Rows 1 to 5 are from after the
fix.

`/code-review` (high) raised five findings. Fixed:

- the next step that asked for a voice platform already connected;
- filtering grants in the database instead of in Python;
- the error boundary;
- feedback on a failed Copy.

The fifth: "Your assistant is doing this. You can close this page." would appear once an
assistant is connected, as the design says. In this build the assistant cannot yet sync
agents or run the first scan (features 6 to 10), so the line would promise more than
works. Dmytro decided to hide it for now ("Hide it for now"); it comes back once the
assistant can do the remaining steps.

**For Dmytro to check on screen**, against `Connexity Onboarding.dc.html`, in dark and
light:

1. Sign up: the app opens on Readiness, 0%, "0 of 4 steps", step 1 open with the command
   and Copy.
2. Copy changes to "Copied" for a moment, and the command is on the clipboard.
3. Run the command in Claude Code and approve the connection. Reload: step 1 is done with
   the assistant's name, the command is gone, 25%, and there is no line under the card.
4. Ask Claude Code to call `get_readiness`: the same steps and next steps.

### Not done

- **"Your assistant is doing this. You can close this page."** is hidden until the
  assistant can do the remaining steps (from feature 6 on).
- **Live updates** (feature 14): the screen reads Readiness when it loads.
- **Steps 3 and 4** stay not started until feature 10 defines them.
- **The Controls card, the sidebar ring and the stripe** (later milestones), and "Using
  another assistant?" (feature 5).
- **Throwaway data in the local dev database:** two play-through users, their
  workspaces, two OAuth clients and two test Retell integrations named "Play-through
  test".
