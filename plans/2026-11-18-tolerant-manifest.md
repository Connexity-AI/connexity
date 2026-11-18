# /mcp-docs survives the services deploying in any order

- **Owner:** Dmytro
- **Slice:** none: a fix after 10.18 (onboarding steps) broke `/mcp-docs` for about two
  minutes while it rolled out on 2026-11-18.
- **Design:** No UI change.
- **MCP:** None needed: no tool changes, and the manifest answers the same.

## Goal

A change to the MCP server's manifest or the backend's onboarding steps can never take
`/mcp-docs` down, whichever service deploys first.

## Decisions

- **Make the fix as a small PR** (Dmytro, 2026-11-18: "sure").

## What happened

On merge, the backend, the MCP server and the web app deploy separately. The new MCP
server went live first without `answer_shape`; the running web app still required it,
rejected the manifest and showed "could not be read" from about 12:35 to 12:37. Then
the new web app asked the backend for the onboarding steps before the backend's new
route was live (404 for a minute; the section was hidden, the page fine). The logs
named both causes.

## Changes

- **The page's manifest schema requires only what it cannot draw without:** the groups
  and their tools' names and lines. Everything else falls back on its own: an unknown
  or missing effect shows as Writes, missing flags as false, missing inputs or guides
  as none, a missing version as "unknown", a missing server URL hides the URL box, and
  the counts are worked out from the groups and guides when missing. Extra fields are
  ignored, as before.
- **The onboarding steps** fall back the same way: a missing actor reads as "Your
  assistant", missing instructions as none; a step without a key or title is dropped.
- **`docs-internal/deployment.md`:** the three services deploy separately on a merge, so
  any change across them must work with either side old for a few minutes: add a field
  before reading it, stop reading it before removing it.

## Done when

- Frontend lint, types and build pass; `make check` passes.
- The schemas parse the live manifest and steps, and also a manifest with
  `answer_shape` added, with a tool's effect unknown, and with `guides` missing (checked
  in a small node script against the schema, as the roadmap session did).

## Out of scope

- Deploying the services in a fixed order.

## Risks

- **A silently thinner page:** a missing field now shows a default rather than an
  error. The server log still says when the manifest cannot be read at all.

## Outcome

### Deviations from the plan

- **A manifest without its tool groups still fails** (the page has nothing to draw);
  everything else falls back.

### Check results

- **The schemas against real and broken answers** (the schema file compiled with
  TypeScript and run with node against `https://mcp.connexity.ai/manifest` and
  `https://api.connexity.ai/api/v1/onboarding/steps`): the live manifest ok; the live
  steps ok; the manifest with `answer_shape` added (the old server) ok; a tool with an
  unknown effect ok, shown as Writes; no guides and no counts ok, counts worked out (30
  tools, 0 guides); steps with a step missing its key and one with an unknown actor and
  no instructions ok (the first dropped, the second shown as "Your assistant"); no
  groups fails, as intended.
- `make check`: every step ok (plan, database, backend lint, pyright, backend tests, MCP
  server tests, frontend lint, frontend types, generated client).
- `/code-review` (high): no findings.

### Not done

- Nothing planned is left.
