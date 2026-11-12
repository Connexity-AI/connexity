# MCP foundation: workspaces, scoping and the standard answer

- **Owner:** Dmytro
- **Slice:** Milestone 1, feature 2 of the roadmap: "MCP foundation".
- **Design:** No UI change.
- **MCP:** Adds `list_workspaces`. Reshapes `list_agents` (takes a workspace, a search
  query and a cursor; answers in the standard shape). Removes `find_agents` (folded into
  `list_agents`) and `get_agent_draft` (a 1.x prompt-draft read). Adds the server's
  connect instructions and the first guides.

## Goal

Every later feature adds MCP tools. This change sets the rules those tools follow, so
the assistant meets one consistent Connexity:

- **Per user.** A connection belongs to the person who approved it and reaches the
  workspaces that person can access (Decided 2026-11-12).
- **Scoped.** Every tool except `list_workspaces` takes a workspace and refuses one the
  person cannot access.
- **One answer shape.** Every tool answers with the facts, the rules that apply,
  numbered next steps and a guide link.
- **Paginated.** List tools take a cursor and a limit and say where the next page starts.

## What exists today

- The MCP server (`mcp_server/`) is a thin adapter: it checks the OAuth token and
  forwards it to backend `/api/v1/mcp/*` routes. OAuth (dynamic client registration,
  PKCE, refresh tokens, sign-up during authorize) lives in the backend. This layering
  stays.
- **Connections are already per user.** The token's subject is the person, and refresh
  tokens are stored per person and client. Nothing to build here.
- **Tokens are pinned to one company.** The authorize step writes the person's company
  into the token (`cid`). Nothing reads it, but it contradicts "reaches the person's
  workspaces".
- **A person belongs to exactly one company** (`user.company_id`), and a company has no
  name. "Workspace" is today's company (Decided 2026-11-12); several workspaces per
  person arrive with "Sign up and log in" (feature 3).
- Three tools: `list_agents` and `find_agents` (no workspace, no shape, the search done
  in the adapter over up to 1,000 agents) and `get_agent_draft` (reads a 1.x prompt
  draft).

## Changes

### Workspace scoping (backend)

- One backend dependency resolves the `workspace_id` of a request against the
  workspaces the person can access. Today that is their one company. In feature 3 it
  becomes their memberships, and only this function changes.
- A workspace the person cannot access answers "Workspace not found", the same as one
  that does not exist, so its existence is not revealed.
- Every backend `/mcp` route takes the workspace in its path:
  `/api/v1/mcp/workspaces/{workspace_id}/…`.
- New tokens no longer carry `cid`.

### The standard answer (backend and adapter)

Every `/mcp` route answers with one envelope, and every tool returns it as is:

| Field | What it holds |
|---|---|
| `data` | The facts: the result of the call |
| `rules` | The rules that apply to what was returned, in a sentence each ("Agents appear once their calls sync; Connexity never edits an agent.") |
| `next_steps` | Numbered steps the assistant can take next, naming the tool to call |
| `guide` | A link to the guide for this part of Connexity |
| `next_cursor` | On lists: where the next page starts, or empty on the last page |

- The backend writes `rules` and `next_steps`, because it knows the state. The adapter
  stays thin.
- Errors use the same shape: a plain message plus the next step ("Call
  `list_workspaces` to see the workspaces you can reach").
- Lists take `cursor` and `limit` (default 25, at most 100).

### Tools

- **`list_workspaces()`** (new): the workspaces the person can access, each with its id
  and name. Next steps say to pass a workspace to every other tool.
- **`list_agents(workspace_id, query?, cursor?, limit?)`** (reshaped): agents in the
  workspace, newest first. The search runs in the database, by name, and replaces
  `find_agents`.
- **Removed:** `find_agents` and `get_agent_draft`, with their backend route, adapter
  code and tests.

### Instructions and guides (adapter)

- **Connect instructions:** when an assistant connects, the server sends short
  instructions: what Connexity is, that every tool needs a workspace, and to start with
  `list_workspaces`.
- **Guides:** short markdown guides served by the MCP server as resources
  (`connexity://guides/<topic>`), linked from the `guide` field. This change ships two:
  "Getting started" and "Workspaces". Each later feature adds its guide.

### Docs

- `docs-internal/mcp-architecture.md`: the envelope, workspace scoping, guides, and how
  to add a tool under these rules. The tool map is updated.
- `mcp_server/README.md`: the current tools.

## Decisions

Decided by Dmytro earlier, applied here:

- A workspace per client. MCP connections are per user and reach exactly that user's
  workspaces, so every call is scoped to one (2026-11-12).
- Every feature ships its MCP tools: few, workflow-shaped, scoped, paginated. They
  answer with facts, the rules that apply and numbered next steps (2026-11-07,
  2026-11-12, `CLAUDE.md` rule 10). The guide link comes from the roadmap entry.

Proposed by Claude:

- The workspace goes in the path of every backend `/mcp` route, and is a required
  argument of every tool except `list_workspaces`.
- An inaccessible workspace answers "not found", not "forbidden".
- The backend writes `rules` and `next_steps`; the adapter passes them through.
- Errors use the same shape.
- A cursor rather than page numbers.
- Tokens stop carrying `cid`.
- Remove `get_agent_draft` and fold `find_agents` into `list_agents`.

## Open questions

1. **How many workspaces a person has in this change.** Recommended: their one company,
   behind the single scoping function; feature 3 adds memberships and workspace
   creation. The alternative is a membership table now, which pulls part of feature 3
   in here.
2. **Workspace names.** A company has no name, and `list_workspaces` should show one.
   Recommended: add `company.name` now, filled from the email domain of the company's
   first user for existing rows, so feature 3 only adds a way to set it.
3. **Where the guide link points.** Recommended: MCP resources served by the server, as
   above, because they reach the assistant without a website. The alternative is public
   web pages, which do not exist yet.
4. **`list_agents` today lists 1.x agents** (created in the product or imported), not
   only synced ones. Recommended: keep it as the first tool on the new rules and reshape
   it again with "Assistant helps choose agents to sync" (feature 7).

## Done when

- `make check` passes. Backend and adapter tests cover:
  - the envelope
  - an inaccessible workspace answering not found
  - pagination to the last page
  - search
  - the token forwarded on every tool call
- Against a running backend and MCP server, with a real OAuth token, played through the
  API and recorded in Outcome:
  1. `list_workspaces` returns the person's workspace with its name, rules, next steps
     and guide.
  2. `list_agents` with that workspace returns its agents in pages, and `next_cursor` is
     empty on the last page.
  3. `list_agents` with another company's workspace answers "Workspace not found" with a
     next step.
  4. `list_agents` with a query returns only matching agents.
  5. Reading `connexity://guides/workspaces` returns the guide.
  6. `find_agents` and `get_agent_draft` are no longer listed.
  7. A token issued after the change has no `cid`.

## Out of scope

- Several workspaces per person, memberships, creating a workspace, agency accounts
  (feature 3 and Milestone 9).
- Listing and revoking connected assistants (the Account page), and ticking Readiness
  when an assistant connects (features 4 and 5).
- Testing the connection from Claude Code and ChatGPT end to end (feature 5).
- Tools for calls, traces, versions, checks and issues; each comes with its feature.
- Rate limits.

## Risks

- **Existing MCP connections break.** Tool names and arguments change. No compatibility
  is owed, but anyone connected must reconnect or adjust.
- **The envelope may be wrong for some tool.** It is set before most tools exist. A
  reviewer should check that every field earns its place, and that `rules` stays short
  and is not used as documentation.
- **The scoping function is the one place access is decided.** If a later route forgets
  to use it, that route leaks across workspaces. A test should fail any `/mcp` route
  without a workspace in its path.

## Outcome

Dmytro accepted the four recommendations with "Accept, build":

1. A person reaches their one company.
2. A company gets a name now.
3. Guides are MCP resources.
4. `list_agents` stays as the first tool on the new rules.

### Deviations from the plan

- **Tokens never carried `cid`.** The plan was wrong about this: the `cid` claim set
  during OAuth authorize is on the web session cookie, not the MCP access token. A token
  issued by the real flow carries `aud, azp, client_id, exp, iat, iss, scope, sub`.
  Nothing changed there.
- **Existing companies are named from one of their users, not the first.** Users have no
  creation time, so the migration takes the user with the lowest id, which is
  repeatable. A company with no user, or an email without a domain, is named
  "Workspace".
- **Extra, from `/code-review`:**
  - A FastAPI 422 (for example a workspace name passed as `workspace_id`) now reaches the
    assistant as a line that names the argument and points to `list_workspaces`, instead
    of "HTTP 422".
  - A cursor with an offset over one billion answers "not valid" instead of failing in
    the database.
  - The scoping guard accepts a route at the workspace root.
- **The adapter's error text** starts with the backend's message, without the old
  "Connexity backend request failed:" prefix. Errors that never reached the backend keep
  the prefix.
- **`app.state.mcp_server`** holds the FastMCP instance, so tests can list tools and read
  guides.
- **A test helper** (`create_test_agent`) takes an optional `name`.

### Check results

`make check` on the final tree, after the review fixes: all checks passed.

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Start local database | ok | 1s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 13s |
| Backend tests and coverage | ok | 80s |
| MCP server tests | ok | 2s |
| Frontend lint | ok | 2s |
| Frontend types | ok | 2s |
| Generated client is fresh | ok | 9s |

Backend MCP route tests: 10 passed. MCP server tests: 16 passed.

The migration applies, reverses and re-applies on the local database. `alembic check`
reports no drift. On the local database, every existing company got a name from an email
domain (counts only; no names reported).

**Played through for real.** The backend ran on port 8001 and the MCP server on port
8012. I registered an OAuth client through the MCP server and signed up two throwaway
users through the OAuth sign-up form with PKCE. I exchanged the codes for tokens, created
three agents for the first user through the web API, and called the tools with the MCP
Python client over streamable HTTP.

| # | Call | Expected | Came back |
|---|---|---|---|
| 0 | Connect | Instructions mention `list_workspaces` | Yes |
| 1 | `list_workspaces` | The person's one workspace, named from the email domain, with rules, next steps and guide | 1 workspace, named after the sign-up domain; 2 rules, 2 next steps, guide `connexity://guides/workspaces` |
| 2 | `list_agents`, limit 2, following `next_cursor` | Every agent once, newest first, last cursor empty | 2 pages; the 3 agents newest first; last `next_cursor` empty |
| 3 | `list_agents` with the other user's workspace | Error "Workspace not found" with a next step | Tool error: "Workspace not found. Next steps: 1. Call `list_workspaces` …" with the guide |
| 4 | `list_agents`, query "dental" | Only the matching agent | 1 agent, "Dental reception" |
| 5 | Read `connexity://guides/workspaces` | The guide | "# Workspaces", `text/markdown` |
| 6 | List tools; call `get_agent_draft` | Only the two tools; the old one unknown | `list_agents`, `list_workspaces`; "Unknown tool: get_agent_draft" |
| 7 | Decode a new token | No `cid` | No `cid` (it never had one; see deviations) |

Row 3 was played before the full stop was added to error messages; the adapter test
covers the new text.

`/code-review` (high) raised six findings; all six are fixed (listed under deviations,
plus `REBUILD.md`, the error text's full stop and the name helper matching the
migration).

### Not done

- **Found, not fixed (outside this feature):** the OAuth sign-up form answers 500 when
  the email fails validation (for example a `.test` domain), instead of showing the form
  with an error. It belongs with "Sign up and log in" (feature 3).
- **Throwaway data left in the local dev database:** two users with their companies and
  three agents, created by the play-through.
- **Not tested from Claude Code or ChatGPT.** That is feature 5. The MCP Python client
  over streamable HTTP stood in for them.
- **Nothing is committed or pushed.**
