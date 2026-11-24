# Usage on the Billing page

- **Owner:** Dmytro
- **Slice:** Usage on the Billing page (roadmap Order 102.45), one pull request.
- **Design:** the prompt in the roadmap row "Balance, included usage and pause"
  (2026-11-23), sections 1 to 5 and 7. The result is already in the repo:
  `designs/screens/Connexity Billing.dc.html`, "Balance and usage" (canvas 1a, 3b) and
  the `billing` section of `Connexity Agency`. The prompt becomes
  `designs/21-billing-usage.md`.
- **MCP:** `get_usage` gains the agency's usage per workspace for an Admin's assistant,
  so it can prepare what to bill each client. Contract entry and input description
  updated.
- **Status:** Approved by Dmytro ("Accept, build", 2026-11-24).

## Goal

An Admin opens Agency settings › Billing and sees what the agency has left, what it used
in a period and what used it, split per client workspace and per agent, and downloads
that as a CSV to bill each client. Nothing here shows Connexity's own model costs.

## What the code is today

- **Billing shows the subscription, the card and the billing details** (pull request
  265). The balance and usage part of the design is not built.
- **What is left is known** (pull request 266): included amount, balance, state, days
  left, served by `GET /agencies/{id}/billing/status`.
- **Usage is read per workspace** (`app/services/usage.py`), by calendar month and by
  when a call happened. The money is drawn by subscription period and by when Connexity
  recorded the usage. The two bases differ (see the question).

## Changes

### What a person sees (as designed)

Above the subscription card, for Admins:

- **Included usage and balance:** "Included this month: $86.40 of $299 left" with one
  thin bar and "Resets 1 Dec"; "Balance: $412.50" with "Used after your included
  amount. Never expires."; under them "Lasts about 3 weeks at your current rate", absent
  when it cannot be told. Out of money, the balance shows in the critical colour.
- **The period:** a picker at the right ("This period", "Last period", "Last 30 days",
  with its dates), a large figure with "used this period", and one thin bar
  split by what used it, with its legend: "Calls observed: 2,140 min · $64.20", "Text
  simulations: 6,160 messages · $123.20". Voice simulations appear only once they
  exist.
- **By workspace:** Workspace, Calls observed, Simulated messages, Cost, sorted by
  cost; a row expands to the workspace's agents; a total row; "Download CSV".
- **What moved it most:** up to three lines with their cost; hidden with nothing to
  show.
- **How it's priced:** the small table with the subscription, the two prices and the
  line about the voice platform billing the agent's replies.
- **A new agency:** balance $0.00, "Your first scan is included: 1,284 calls checked"
  (or "the latest 500 calls of 3,410 checked"), and "No usage yet" in place of the bar
  and table.
- **A Member** keeps seeing "Only Admins can see billing. Ask …".
- **Not shown,** because nothing behind them works yet: Add funds, auto top-up,
  invoices, the failed-payment line.

### Backend

- **`GET /agencies/{id}/billing/usage?period=`:** for Admins. The period's start and
  end, the total, the split by meter (units and dollars), each workspace with its
  agents (deleted workspaces and agents by their kept names), and the three things that
  added most. Dollars are units times the list price.
- **`GET /agencies/{id}/billing/usage.csv?period=`:** the same per workspace and agent,
  one row each: workspace, agent, observed minutes, simulated messages, cost.
- **No own costs:** neither route returns `own_cost_usd`, tokens or a model name.

### Assistants

- **`get_usage` with `agency: true`:** for an Admin's assistant, the same per-workspace
  figures for the agency of the given workspace. A Member's assistant is told only
  Admins can see billing.

### Docs

- `docs-internal/billing.md` (the page, the usage routes, the bases), `usage.md`,
  `mcp-architecture.md`, `designs/README.md`, `designs/21-billing-usage.md`.

## Decisions

- **Decided (Dmytro, 2026-11-23, roadmap rows):** dollars only; no credits; one
  subscription; only Admins; Connexity's own model costs and margin are never shown; a
  CSV so the agency can bill each client.
- **Proposed:** `get_usage` gains the agency level, for Admins' assistants only.
- **Proposed:** the CSV has one row per workspace and agent for the picked period, with
  a total row.
- **Decided (Dmytro, 2026-11-24):** the page counts in subscription periods, by when
  Connexity recorded the usage, so it always adds up to what is left. The picker reads
  "This period", "Last period" and "Last 30 days", with the dates shown. An agency with
  no subscription sees the last 30 days.

## Done when

- Through the API on the local database: the usage route's total equals the sum of its
  workspaces, each workspace the sum of its agents, and the split by meter the same
  total; a deleted workspace's usage still appears under its name; the CSV has the same
  rows and total; a Member, an outsider and an assistant are refused on the web routes;
  no answer contains an own cost.
- `get_usage` with `agency` answers the same figures for an Admin's assistant and
  refuses a Member's.
- MCP server tests pass with the new input and contract text.
- Frontend types and lint pass; the full `make check` passes.

## Out of scope

- Add funds, auto top-up, invoices, the failed-payment states and emails (row "Top-ups,
  invoices and payment emails").
- Charts beyond the one thin bar; a view per day.
- Voice simulation minutes: they do not exist yet.

## Risks

- **Figures that do not add up to the balance lose trust at once.** The page uses the
  same basis as the money; a test checks that "this period" equals what was drawn.
- **The assistant's per-workspace `get_usage` still counts by calendar month and by
  when a call happened.** Its agency answer uses the subscription period; the guide says
  which is which.

## Outcome

### Deviations from the plan

- **The balance and usage sit under the subscription card,** as in the design, not
  above it as the plan said.
- **"Included this period"** in place of the design's "Included this month", following
  the decision on periods. The big figure reads "used this period · 24 Nov to 24 Dec".
- **The period picker shows only the periods that exist:** all three with a
  subscription, none without one (only the last 30 days exist then).
- **A deleted workspace's line carries a "Deleted" chip,** which the design does not
  have: the workspace is gone from every other screen.
- **The prices in "How it's priced" come from the server,** so they cannot drift from
  what is charged.
- **`get_usage` took a second input, `agency_period`,** beside `agency`.
- **An Admin's assistant gets `agency_usage` also where paying is not set up** (then
  for the last 30 days): the usage exists there too.
- **A new column and migration** (`agency.first_subscribed_at`, `0053`), added with the
  first-scan fix. For an agency that already has a subscription it is filled with its
  current period's start, the earliest start that is known.

### Check results

Route tests through the API on the local database (`TestClient`; no separate
play-through server):

| What | Result |
|---|---|
| `test_billing_usage.py` (6 tests): this period's total equals the sum of its parts, of its workspaces and of each workspace's agents, sorted by cost, and is exactly what came off the included amount; the last period and the last 30 days count what belongs to them, and an agency without a subscription is offered only the last 30 days; a deleted workspace's usage stays under its name; the CSV has one row per workspace and agent, the same total, and a name that starts like a formula made safe; a Member, an outsider and an assistant are refused on the web routes; an Admin's assistant gets the agency's usage, a Member's is refused and still reads its own workspace; no answer contains Connexity's own cost or a model name; the included first scan is never shown as money spent, in any period or in the CSV | passed |
| MCP server tests (69), with the two new inputs and their descriptions | passed |
| Backend `ruff` and `pyright`; frontend types, lint and formatting; client regenerated | passed |
| Full `make check`, after the review fixes, the first-scan fix included | passed, every step |

For Dmytro to check on screen, with the sandbox key in `.env` (dark, light and phone
width, against "Balance and usage" in `designs/screens/Connexity Billing.dc.html`):

1. With a sandbox subscription: "Included this period", the bar, "Resets …",
   "Balance", and under them the big figure with its dates.
2. The picker switches between "This period", "Last period" and "Last 30 days" without
   leaving the page.
3. "By workspace": sorted by cost, a row opens to its agents, the total row, and
   "Download CSV" saves a file that opens in a spreadsheet.
4. Without a subscription: no "Included", balance $0.00, the first-scan line, and "No
   usage yet" when nothing was used in the last 30 days.
5. As a Member: still only "Only Admins can see billing. Ask …".

### Code review

Two findings:

- **Fixed:** two lines under "What moved it most" could share a label and a key (two
  test runs on one agent on one day). They are now keyed by position.
- **Fixed after Dmytro's decision ("Yes, fix it", 2026-11-24):** the included first
  scan showed up as money spent in "Last period", "Last 30 days" and their CSV, though
  it was never charged. The date an agency's first subscription began is now kept
  (`agency.first_subscribed_at`, migration `0053`), and usage recorded before it is
  left out of every figure on the page, in the CSV and in the assistant's
  `agency_usage`. An agency that never subscribed sees "No usage yet". Where paying is
  not set up nothing is charged, and everything is shown at list price. Tested.

### Not done

- The screen was not opened in a browser, and the CSV download was not clicked: the
  route is tested, the link through the app's proxy is not.
- "Lasts about 3 weeks" and the split bar with real figures need usage that is slow to
  produce by hand; their logic is tested on the server.
- No frontend test: the app has none.
