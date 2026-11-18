# Deployment notes for MCP_URL and the Jev key, and why /mcp-docs fails

- **Owner:** Dmytro
- **Slice:** none: a follow-up to 10.17 (MCP contract page) and 10.14 (Jev), after both
  went live on 2026-11-18.
- **Design:** No UI change.
- **MCP:** None needed: nothing a user can do or see through the assistant changes.

## Goal

The next deploy cannot miss the settings these features need, and when `/mcp-docs`
cannot read the contract, the server log says why.

## Decisions

- **Small PR with the logging and the deployment notes** (Dmytro, 2026-11-18: "Yes,
  small PR").
- **Set in production on 2026-11-18, with Dmytro's approval:** `MCP_URL` on
  `connexity-ui` (revision `connexity-ui-00157-ndb`), and the secret
  `connexity-typesafe-api-key` mounted on `connexity-backend` as `TYPESAFE_API_KEY`
  (revision `connexity-backend-00169-l42`). This PR records them; it changes no
  service.

## Changes

- **`/mcp-docs`** logs one line on the server when it cannot read the manifest:
  `MCP_URL` not set, the server's HTTP status, a network error's type, or that the
  answer did not match the expected shape (with the fields that did not). The page
  itself is unchanged.
- **`docs-internal/deployment.md`:**
  - the secrets table gains `connexity-typesafe-api-key` (backend `TYPESAFE_API_KEY`);
  - a note on each service's plain settings that matter here: the web app's
    `API_URL`, `SITE_URL` and `MCP_URL`;
  - no Anthropic key in production yet: no judge check is registered.

## Done when

- Frontend lint and types pass; `make check` passes.
- With `MCP_URL` unset locally, `/mcp-docs` logs "MCP_URL is not set" on the server.

## Out of scope

- Any change to a running service.
- An Anthropic key in production (when a judge check is registered).

## Risks

- None worth a reviewer's time.

## Outcome

### Deviations from the plan

None.

### Check results

- Frontend lint and types: ok.
- `make check`: every step ok (plan, database, backend lint, pyright, backend tests, MCP server tests, frontend lint, frontend types, generated client).
- `/code-review` (high): no findings.

### Not done

- **The log line was not seen running:** no local web server was started (Dmytro
  checks screens). To see it, run `make dashboard` with `MCP_URL` unset and open
  `/mcp-docs`: the terminal shows "/mcp-docs could not read the MCP manifest: MCP_URL is
  not set".
