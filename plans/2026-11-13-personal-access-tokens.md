# Frictionless assistant connection (personal access tokens)

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Frictionless assistant connection (personal
  access tokens)".
- **Design:** Readiness step 1 follows the design adjustment on the roadmap feature's page
  (two tabs, "Copy setup prompt"), built only after Dmytro applies it in Claude Design and
  exports `Connexity Onboarding.dc.html` again; the current export (2026-11-12) still shows
  the old `claude mcp add` snippet. Account › Assistant access follows
  `Connexity Account.dc.html` (export 2026-11-12), section 3 only. `designs/12-adjustments.md`
  items 19 and 23.
- **MCP:** no new tools (Decided by Dmytro, 2026-11-13). The MCP server accepts a personal access
  token wherever it accepts an OAuth token, so every existing tool works with either. The
  connect instructions, the `connect` guide and `get_readiness` change.

## Goal

A person connects Claude Code, in the app or the terminal, without a browser sign-in:
they press **Copy setup prompt** on Readiness, paste it into Claude Code, and Claude adds
Connexity itself. Step 1 ticks the first time the assistant calls Connexity. Today the
Claude Code app cannot do the OAuth sign-in at all: a server added with `claude mcp add`
that needs OAuth stays hidden there, and only `/mcp` in a terminal can sign it in.

OAuth stays for Claude.ai and ChatGPT connectors. Both use the new address
`https://mcp.connexity.ai/mcp` instead of the Cloud Run one.

## Changes

### Personal access tokens (backend)

- **A new kind of credential**, owned by a person, not a workspace: `personal_access_token`
  with the person, a name, the first characters for recognising it (`cxp_` plus a few),
  a SHA-256 hash of the token, created, last used and revoked times. The token itself is
  `cxp_` plus 32 random bytes, returned once and never stored. Same pattern as the ingest
  tokens from slice 1.2; the hashing helper is shared.
- **Never expires** until revoked (Decided by Dmytro, 2026-11-13).
- **Reaches exactly that person's workspaces**, like an OAuth connection: the token
  carries no workspace, and access is still decided in `crud/workspace.py`.
- **Web routes** (cookie sign-in, the person's own tokens only):
  - `POST /api/v1/personal-access-tokens`: creates a token named "Claude Code" and answers
    with the token and the setup prompt, ready to copy. Creating one revokes this
    person's earlier tokens that were never used (Proposed, so pressing the button twice
    does not leave stray working tokens).
  - `GET /api/v1/personal-access-tokens`: name, prefix, created, last used. Revoked tokens
    are not listed.
  - `DELETE /api/v1/personal-access-tokens/{id}`: revokes it. The next call with it is
    refused.
- **MCP routes accept it.** `require_mcp_user` takes either an OAuth access token (as
  today) or a personal access token: found by hash, not revoked, its person active. "Last
  used" is written at most once a minute per token. Records of who did what name the
  token's name ("Claude Code") where they name the OAuth client today.
- **A check route for the MCP server**, `GET /api/v1/mcp/token`: answers 200 for a
  usable token of either kind and 401 otherwise. Nothing else.

### MCP server

- **Token verification** accepts both kinds. A bearer starting with `cxp_` is checked
  with the backend route above (result cached for 60 seconds); anything else is verified
  as a signed OAuth token, as today. A rejected token gets the same 401 as today.
  Revocation takes effect on the next tool call, because the backend checks every call;
  the cache only affects the connection handshake.
- **Connect instructions** say what to do right after connecting: call
  `list_workspaces`, then `get_readiness`, and follow its first next step (onboarding
  continues from there: connect Retell, add agents, set the webhook, first scan).
- **The `connect` guide**: Claude Code connects with a setup prompt from Readiness; the
  OAuth route (`/mcp` in a terminal) stays as the fallback. Claude.ai and ChatGPT use
  `https://mcp.connexity.ai/mcp`.

### Readiness

- Step 1 is done while a person in the workspace has a personal access token that has
  been used and is not revoked, or an OAuth connection (as today). Its detail names them:
  "Claude Code".
- The answer drops `connect_command` and gives `mcp_url`
  (`https://mcp.connexity.ai/mcp`), which the Claude.ai or ChatGPT tab shows.

### The setup prompt

Copied by the button, never shown in full on screen. Draft:

> Connect Connexity to Claude Code. Run this command, and do not repeat the token in your
> reply: `claude mcp add --transport http --scope user connexity
> https://mcp.connexity.ai/mcp --header "Authorization: Bearer cxp_…"`. Then tell me to
> start a new Claude Code session, where Connexity's tools load. In it, call
> `list_workspaces` and `get_readiness` and follow the next steps.

Whether a new session is needed, or the running one picks the server up, is checked in
the Claude Code app and terminal while building; the prompt says whatever is true.

### Screens

- **Readiness step 1**, while no assistant is connected: two tabs, **Claude Code** and
  **Claude.ai or ChatGPT**, as in the design adjustment. "Copy setup prompt" creates the
  token and copies the prompt; the muted line under it says the token can be revoked in
  Account. The step ticks on its own (Readiness already refreshes) and shows "Connected:
  Claude Code".
- **Account page** with one section, **Assistant access**: this person's tokens, each with
  name, "Created 13 Nov", "Last used 2 h ago" or "Never used", and **Revoke** (asks to
  confirm). The design's line "Anything your assistant does is recorded as done by your
  assistant on your behalf." The other Account sections are not built (rule 14).
- **Profile menu** gains **Account**, which opens that page.

### mcp.connexity.ai

- Cloud Run domain mapping `mcp.connexity.ai` → `connexity-mcp`, the same way
  `app.connexity.ai` is mapped to `connexity-ui` (the domain is already verified).
- A DNS record in Cloudflare: `mcp` CNAME `ghs.googlehosted.com`, DNS only (not proxied).
  **Dmytro adds it**; the session has no access to Cloudflare.
- Once the certificate is issued, the MCP service gets
  `MCP_PUBLIC_BASE_URL=https://mcp.connexity.ai` and
  `MCP_OAUTH_AUDIENCE=https://mcp.connexity.ai/mcp`, and the backend gets the same
  `MCP_OAUTH_AUDIENCE`. The OAuth issuer stays the backend's address.
- `docs-internal/deployment.md` records the mapping and the new settings.

### Docs

`docs-internal/mcp-architecture.md` (two kinds of token, the check route, how revocation
works), `deployment.md`, the `connect` guide, and the status line in `REBUILD.md`.

## Decisions

- Personal access tokens alongside OAuth; OAuth stays for Claude.ai and ChatGPT. Decided
  by Dmytro, 2026-11-13.
- Tokens never expire until revoked, are shown once, stored hashed, and reach exactly
  that person's workspaces. Decided by Dmytro, 2026-11-13.
- Step 1 ticks on the token's first use; tokens listed in Account › Assistant access with
  Revoke; `mcp.connexity.ai` mapped to the MCP service. Decided by Dmytro, 2026-11-13
  (roadmap entry).
- The token row belongs to a person and has no `company_id`, like OAuth refresh tokens.
  Proposed.
- The MCP server asks the backend about `cxp_` tokens instead of reading the database.
  Proposed; it keeps the rule that `mcp_server/` holds no database or access logic.
- A new copy revokes this person's never-used tokens. Proposed.
- Domain mapping rather than a load balancer: free and already used for the app.
  Proposed.
- No MCP tools to create or revoke tokens: an assistant does not manage the credential
  it runs on. Decided by Dmytro, 2026-11-13.
- Account › Assistant access lists personal access tokens only; OAuth connections come
  with the Account feature. Decided by Dmytro, 2026-11-13.
- The backend, MCP and Account parts are built first; the Readiness step 1 tabs follow
  Dmytro's new export, in this same pull request. Decided by Dmytro, 2026-11-13.
- The OAuth issuer stays the backend's Cloud Run address. Decided by Dmytro, 2026-11-13.

## Done when

Against the running backend and MCP server (local), recorded in the Outcome:

- `POST /personal-access-tokens` answers the token once and the prompt containing it; a
  second `POST` revokes the first while it is unused; `GET` never shows a token.
- An MCP call with the token reaches `list_workspaces` and lists exactly that person's
  workspaces; a workspace they cannot reach answers 404.
- After the first call, `get_readiness` step 1 is done with "Claude Code" for every
  workspace the person is in, and not for a workspace they are not in.
- After `DELETE`, the next MCP tool call and the MCP handshake (after the cache) answer
  401; step 1 goes back to not done when no other connection exists.
- A made-up `cxp_` token, another person's revoked token, and a token of a deactivated
  person are refused.
- OAuth tokens keep working exactly as before (existing tests pass).
- Records of who did what (for example `connect_voice_platform`) name "Claude Code" when
  done with a token.
- `make check` passes; backend and adapter tests cover the above.

Live, after merge:

- `https://mcp.connexity.ai/.well-known/oauth-protected-resource` answers with
  `resource: https://mcp.connexity.ai/mcp`.
- For Dmytro to check: the setup prompt in the Claude Code app connects and the tools
  load; Readiness step 1 ticks on its own; Revoke in Account cuts it off; Claude.ai (or
  ChatGPT) still connects with OAuth at the new address.

## Out of scope

- The rest of the Account page (profile, password, sessions, notifications, delete).
- Listing and revoking OAuth connections (the Account feature).
- Token scopes, per-workspace tokens, expiry.
- An `api.connexity.ai` address for the backend.
- Retiring the Cloud Run `*.run.app` addresses; they keep working.

## Risks

- **Existing OAuth connections break once.** Changing the audience means tokens issued
  for the old address are refused; Claude.ai and ChatGPT connections must be added again
  with the new address. Only Dmytro's test connections exist today.
- **The token sits in plain text** in Claude Code's config (`~/.claude.json`) and in the
  conversation where the prompt was pasted. That is the trade for no sign-in; Revoke is
  the answer if it leaks. A reviewer should push back if the prompt or the guide ever
  asks the assistant to print it.
- **Certificate timing.** The mapping's certificate can take up to an hour after the DNS
  record exists; the settings switch waits for it, or OAuth discovery breaks.
- **Order of deploys.** Backend, MCP server and app deploy from separate triggers, so
  for a few minutes after the merge the app may hand out a token that the MCP server
  does not accept yet. Harmless (the token works once both are live), but the live check
  waits for all three. The MCP service's new address settings are applied by hand after
  the certificate is issued.

## Outcome

Written while the Readiness step 1 tabs still wait for Dmytro's design export; this
section is completed when they are built.

### Deviations from the plan

- **No separate check route.** The MCP server checks a `cxp_` token by calling the
  existing `GET /api/v1/mcp/workspaces` with it: a 200 means the token works. Same
  result, one route fewer, and no exception to the rule that every other `/mcp` route
  is scoped to a workspace.
- **Account rows follow the design, not the plan's text.** Each row shows the token's
  name and "Reaches N workspaces", with Revoke, as in `Connexity Account.dc.html`. The
  plan said "Created 13 Nov · Last used 2 h ago"; that is not in the design, so it is not
  on screen. "Last used" is in the API (`last_used_at`). Revoke has no confirmation step,
  also as in the design.
- **The web routes' tag is `tokens`**, so the generated client reads
  `TokensService.listPersonalAccessTokens` instead of a doubled prefix.
- **Readiness keeps its current snippet until the tabs are built.** The backend no
  longer sends `connect_command`; the screen builds the same command from `mcp_url`.
- **The domain mapping and the Cloudflare record already existed** (created 2026-11-13,
  12:48 UTC). The certificate was still being issued at the time of writing.

### Check results

`make check` (with the branch's own test database): every step passed except "Plan
present and complete", which passes once this Outcome is complete.

| Step | Result |
|---|---|
| Backend lint and format | ok (after `ruff --fix` sorted one import block) |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

API calls against a local backend and MCP server, two people (Ann and Bob):

| Request | Expected | Got |
|---|---|---|
| POST /personal-access-tokens | 201, `cxp_` token inside the setup prompt | 201, token in prompt, `--scope user` present |
| POST again, then GET | first (unused) revoked; list has only the second, no token | as expected |
| MCP `list_workspaces` with the first token | 401 | 401 |
| GET /readiness before first use | step 1 not started, `mcp_url` set | as expected |
| MCP `list_workspaces` with the second token | 200, exactly Ann's workspace | 200, 1 workspace |
| MCP `get_readiness` for Bob's workspace with Ann's token | Workspace not found | Workspace not found |
| MCP `get_readiness` for Ann's workspace | step 1 done, "Claude Code" | done, "Claude Code" |
| GET /readiness as Bob | step 1 not started | not started |
| GET /personal-access-tokens after use | `last_used_at` set | set |
| MCP with a made-up `cxp_` token, and with garbage | 401 | 401, 401 |
| DELETE Ann's token as Bob | 404 | 404 |
| DELETE as Ann | 204 | 204 |
| Backend `/mcp/workspaces` right after revoke | 401 | 401 |
| MCP tool call within a minute of revoke | refused | "Unauthorized" from the tool |
| MCP after the 60-second cache | 401 | 401 |
| GET /readiness after revoke | step 1 not started | not started |

Backend tests also cover: a deactivated person's token, the web session token refused
as an MCP token, "last used" written at most once a minute, step 1 ticking in a second
workspace of the same person, and `connect_voice_platform` recording "Ann through Claude
Code" for a token. Adapter tests cover the backend check, its 60-second cache, a refusal
not being cached, and the backend being down.

For Dmytro to check on screen:

- The profile menu has **Account** under the workspaces; it opens Account with one
  section, Assistant access.
- After copying a token (for now via the API or, once built, the Readiness button) and
  using it once, the token appears there as "Claude Code · Reaches N workspaces";
  **Revoke** turns it to "Revoked" and the assistant is refused.
- Readiness step 1 still shows the `claude mcp add` snippet, now with the address from
  `mcp_url`.

### Not done

- **Readiness step 1 tabs and "Copy setup prompt"**: waiting for the design export.
  The plan said Readiness already refreshes; it does not (it loads once), so the step
  ticking "on its own" needs a refresh while the step is open. Built with the tabs.
- **The live switch to `mcp.connexity.ai`**: the MCP service's `MCP_PUBLIC_BASE_URL` and
  `MCP_OAUTH_AUDIENCE` and the backend's `MCP_OAUTH_AUDIENCE` are changed after merge,
  once the certificate is issued. Not yet done.
- **Whether Claude Code needs a new session** after `claude mcp add`: not checked yet;
  the prompt currently says to start one.
- `/code-review`: run when the pull request is complete.
- The migration is `0014_personal_access_token` on top of `0013`. The first-scan branch
  also adds a `0014`; whichever merges second moves its `down_revision`.
