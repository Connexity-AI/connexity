# Fix: every page answered 500 once the sidebar had a page

- **Owner:** Dmytro
- **Slice:** Fix to Demo 10.07 (Calls page, #194). No roadmap feature of its own.
- **Design:** No UI change.
- **MCP:** None needed: the web app's shell only.

## Goal

app.connexity.ai renders again. Since #194 added Calls to the sidebar, every page with
the sidebar, Readiness included, answered "500 - Server Error" (Dmytro, 2026-11-13,
error id 3395057305).

## What went wrong

The sidebar (a server component) passed each nav item, with its icon component, to
`NavLink` (a client component). React cannot send a function from the server to a
client component: "Functions cannot be passed directly to Client Components". Until
#194 the sidebar had no items, so nothing was passed and nothing failed. Lint, types and
`next build` all pass with the bug; it shows only when a signed-in page renders.

## Changes

- **The sidebar renders each icon itself** and passes the element (not the component)
  to `NavLink`, with the item's title and address.
- **`NavLink` compares addresses without their trailing slash,** so Calls is marked as the
  open page on `/calls/` and on a single call (`/calls/{id}/`). Before, `/calls/` never
  matched a call page.

## Decisions

Proposed by Claude: pass rendered elements across the server-client line, never
components.

## Done when

- `make check` and `pnpm build` pass.
- Rendered signed in on a locally running app: `/` and `/calls/` answer 200 with the
  Calls link in the sidebar; the same check on `main` without the fix answers 500 with the
  same error.
- After merge, app.connexity.ai opens again.

## Out of scope

- A test that renders signed-in pages in CI (worth adding; its own work).

## Risks

- None beyond the shell.

## Outcome

### Deviations from the plan

None.

### Check results

| Check | Result |
|---|---|
| `make check` | All steps ok |
| `pnpm build` | ok |
| Local app on `main` without the fix, `/` signed in | 500, "Functions cannot be passed directly to Client Components" (as in production) |
| Local app with the fix, `/` and `/calls/` signed in | 200 each, Calls link in the sidebar, no errors in the log |

**For Dmytro to check on screen after merge:** app.connexity.ai opens on Readiness, the
sidebar shows Calls, and Calls is highlighted on the Calls page and on a single call.

### Not done

- **A signed-in render in CI,** which would have caught this. It is its own work.
