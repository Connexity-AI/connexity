# Connect Claude Code and ChatGPT

- **Owner:** Dmytro
- **Slice:** Milestone 1, feature 5 of the roadmap: "Connect Claude Code and ChatGPT".
- **Design:** for the backend part, no UI change. The "Using another assistant?" link
  on Readiness depends on question 2.
- **MCP:** no new tools. Every tool gains the hints both assistants read (read-only or
  not), so ChatGPT asks before `create_workspace` and not before the read tools.

## Goal

A person can connect both Claude Code and ChatGPT to Connexity through MCP, sign in,
approve, and use the tools. Readiness step 1 then ticks (built in feature 4). Dmytro
tests both.

## What is wrong today

Both assistants are refused at the first step, client registration. Our OAuth server
accepts only Claude.ai's callback addresses (`https://claude.ai/api/mcp/auth_callback`
and the `claude.com` one). From the two vendors' own docs:

- **Claude Code** registers with Dynamic Client Registration and a loopback callback on
  a port that changes every session, for example `http://localhost:3118/callback`. The
  server must match `localhost` and `127.0.0.1` with the port ignored (RFC 8252).
- **ChatGPT** registers with Dynamic Client Registration (or a Client ID Metadata
  Document) and uses one of two callbacks:
  - `https://chatgpt.com/connector_platform_oauth_redirect`, when the server returns
    `iss` in every authorization response (RFC 9207) and advertises it;
  - otherwise `https://chatgpt.com/connector/oauth/{callback_id}`, which changes per
    connection.

What already matches both: PKCE with S256, public clients (`none`), refresh tokens with
rotation, the `resource` parameter, protected resource metadata, and a 401 with
`WWW-Authenticate` pointing at it.

Sources: Claude's connector authentication docs
(claude.com/docs/connectors/building/authentication) and OpenAI's Apps SDK auth docs
(developers.openai.com/apps-sdk/build/auth).

## Changes

### OAuth server (backend)

- **Loopback callbacks (RFC 8252):** registration and authorization accept
  `http://localhost`, `http://127.0.0.1` and `http://[::1]` callbacks on any port. A
  registered loopback callback matches a request with the same host and path on any
  port. Only plain `http` is allowed on loopback, nothing else on `http`.
- **ChatGPT's callbacks:** `https://chatgpt.com/connector_platform_oauth_redirect`, and
  any `https://chatgpt.com/connector/oauth/{callback_id}`, matched by that exact shape.
- **Issuer identification (RFC 9207):** every authorization response carries `iss`
  (the issuer, exactly as in the metadata): the code redirect and the `access_denied`
  redirect. The metadata advertises `authorization_response_iss_parameter_supported:
  true`. ChatGPT then uses its stable callback.
- The allow list for other callbacks (`OAUTH_ALLOWED_REDIRECT_URIS`) stays as it is.

### MCP server

- Tool hints: `list_workspaces`, `list_agents` and `get_readiness` are read-only and
  touch nothing outside Connexity (`readOnlyHint`, `openWorldHint: false`).
  `create_workspace` is not read-only and not destructive.

### Docs

- `docs-internal/mcp-architecture.md`: which clients are supported, their callbacks, and
  why `iss` matters.
- A guide for people, served as `connexity://guides/connect` and linked from the
  answers: how to connect Claude Code (the command) and ChatGPT (developer mode, add a
  connector with the MCP address, sign in, approve).

## Decisions

Decided earlier, applied here:

- MCP connections are per user and reach that person's workspaces (2026-11-12).
- The assistant is the main way in. Connexity serves MCP; the person approves the
  connection (`who-does-what.md`).

Proposed by Claude:

- Accept loopback callbacks on any port for every client, as RFC 8252 says, rather than
  only for a named Claude Code client: Cursor, Codex and other CLIs work the same way.
- Accept only ChatGPT's two documented callback shapes, not any `chatgpt.com` address.
- Return `iss` everywhere, so ChatGPT uses its stable callback.
- No Client ID Metadata Document support yet. Both assistants fall back to Dynamic
  Client Registration when the server does not advertise it.
- No `offline_access` scope: refresh tokens are issued whenever the client registered
  for them, which both do.

## Answered questions

Dmytro accepted the plan ("accept build", 2026-11-12):

1. ChatGPT is tested on the hosted deployment, app.connexity.ai, after merge ("Its
   already automatically deployed on merge so i will test on app.connexity.ai"). Claude
   Code is tested there too.
2. "Using another assistant?" stays out; the ChatGPT steps go in the Connect guide.
3. The ChatGPT plan used for testing was not stated.

## Done when

- `make check` passes. Backend tests cover:
  - registering with `http://localhost/callback` and authorizing with
    `http://localhost:53122/callback` (and the same for `127.0.0.1`);
  - refusing `http://evil.example.com/callback` and `https://localhost:1/callback` on
    a non-loopback host;
  - ChatGPT's two callbacks accepted, and `https://chatgpt.com/other` refused;
  - `iss` on the code redirect and the `access_denied` redirect;
  - the metadata flag.
- Played through on the running servers with a client that registers like Claude Code
  (a loopback callback, a new port at authorize) and one like ChatGPT (its stable
  callback): register, sign in, Allow, token, call `list_workspaces`.
- **Dmytro:**
  1. In Claude Code, `claude mcp add --transport http connexity <MCP address>`, sign
     in, Allow, then "list my Connexity workspaces"; Readiness step 1 shows "Claude Code".
  2. In ChatGPT developer mode, add a connector with the MCP address, sign in, Allow,
     then ask it to list the workspaces; Readiness shows ChatGPT too.

## Out of scope

- Client ID Metadata Documents and `private_key_jwt`.
- Listing or revoking connected assistants (the Account page).
- Other assistants (Cursor, Codex). They should work through the loopback rule, but
  they are not tested here.
- "Using another assistant?" (question 2).

## Risks

- **Loopback callbacks on any port** let any local program that registers a client
  receive a code for it. That is how native apps work (RFC 8252). The person still sees
  "Connect … to Connexity" with the client's name and must press Allow. The name is
  chosen by the client, though, so it can claim to be anything; a reviewer should weigh
  that.
- **ChatGPT's behaviour changes often.** The docs and community reports disagree on
  details: plans, CIMD versus registration, and tools not appearing after sign-in.
  Dmytro's test is the real check.
- **ChatGPT may need more than OAuth to show the tools** (per-tool `securitySchemes`).
  If the tools do not appear after sign-in, that is the next thing to add.

## Outcome

### Deviations from the plan

- **ChatGPT's per-connection callback** is matched as one path segment of unreserved URL
  characters (letters, digits, `.`, `_`, `~`, `-`, up to 256), because the docs do not
  say what a callback ID looks like (from `/code-review`).
- **The Connect guide** has the steps for Claude Code (`claude mcp add …`, then `/mcp` to
  authenticate) and ChatGPT (developer mode, a connector with the MCP address, OAuth).
  ChatGPT's menu names come from its help pages and may move.
- **Testing on app.connexity.ai:** a merge deploys the backend and the MCP server through
  Cloud Build. No other changes were needed for that.

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

- `app/tests/core/test_oauth_redirects.py` (22). Allowed:
  - Claude.ai;
  - loopback on and off a port, `127.0.0.1` and `[::1]`;
  - ChatGPT's two shapes.

  Refused:
  - other hosts, `https` on loopback, `localhost.evil.com`;
  - user info, fragments, a bad port;
  - other `chatgpt.com` paths, a look-alike host, `http` ChatGPT.

  Loopback matches any port, but not another host, path or scheme.
- `test_oauth.py`:
  - Claude Code with a loopback callback on a new port, receiving `iss`;
  - ChatGPT with its stable callback;
  - a loopback client cannot send a code elsewhere;
  - the metadata flag;
  - `iss` on Cancel.
- MCP server: the tool hints (19 tests).

**Played through on running servers** (backend on port 8001, MCP server on port 8012), with
the MCP Python client over streamable HTTP:

| Client | Registered, then used | Came back |
|---|---|---|
| Like Claude Code | `http://localhost/callback`, then `http://localhost:53122/callback` | Register 200; consent "Connect Claude Code to Connexity"; Allow 303 to port 53122 with `iss`; token with a refresh token; the 4 tools; Readiness step 1 "Claude Code" |
| Like ChatGPT | `https://chatgpt.com/connector_platform_oauth_redirect` | The same: 303 to ChatGPT's callback with `iss`; Readiness step 1 "ChatGPT" |
| Like ChatGPT, per connection | `https://chatgpt.com/connector/oauth/cb_123` | The same |
| Anything else | `http://evil.example.com/cb` | Register 400 |

The metadata reports `authorization_response_iss_parameter_supported: true`, and
`create_workspace` is not read-only while the others are.

`/code-review` (high) raised three findings:

- **Fixed:** the narrow ChatGPT callback ID pattern.
- **Not fixed:** a local program can register a loopback client under any name, so the
  approval page shows a name the client chose (see Risks).
- **Not fixed:** the hosted issuer settings must match exactly (see Not done).

**For Dmytro, on app.connexity.ai after merge:**

1. Claude Code: run `claude mcp add --transport http connexity <MCP address>` (the
   command on Readiness), then `/mcp` and authenticate. Sign in and Allow, then ask
   "list my Connexity workspaces". Readiness step 1 shows "Claude Code".
2. ChatGPT: in developer mode, add a connector with the MCP address and OAuth. Sign in,
   Allow, turn the connector on in a chat, and ask for the workspaces. Readiness shows
   ChatGPT.
3. If ChatGPT signs in but shows no tools, tell me: the next step is per-tool
   `securitySchemes` (see Risks).

### Not done

- **Not tested with the real Claude Code or ChatGPT.** That is Dmytro's test on
  app.connexity.ai.
- **Hosted settings must match exactly.** The backend's `OAUTH_ISSUER_URL` must equal the
  MCP server's `MCP_OAUTH_ISSUER_URL`, with no trailing-slash difference. ChatGPT compares
  the metadata's issuer, the protected resource metadata's authorization server and
  `iss`. If ChatGPT reports an issuer mismatch, check these two.
- **Client ID Metadata Documents** and per-tool `securitySchemes`.
- **"Using another assistant?"** on Readiness (answered: later, with a design).
- **Throwaway data in the local dev database:** three play-through users and their OAuth
  clients.
