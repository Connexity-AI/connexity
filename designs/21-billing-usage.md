# 21. Billing: balance and usage

The Claude Design prompt for the balance and usage on Agency settings › Billing, from
the roadmap rows "Balance, included usage and pause" and "Usage on the Billing page"
(2026-11-23). The result is "Balance and usage" in
`screens/Connexity Billing.dc.html`, the `billing` section of
`screens/Connexity Agency.dc.html`, the sidebar line in `screens/Connexity Sidebar.dc.html`
and the stripes in `screens/Connexity Readiness Bar.dc.html`. How it works:
[`docs-internal/billing.md`](../docs-internal/billing.md).

Built: all seven sections. Two things differ from the prompt by Dmytro's decisions of
2026-11-24: the first scan's limit is 500 calls per agency, and the usage is counted in
subscription periods ("This period", "Last period", "Last 30 days"), not calendar
months, so it adds up to what is left.

```txt
Update Agency settings › Billing (Connexity Agency) for the balance and usage, in dark and light. Keep the existing page layout and design system. Sentence case, plain words, no exclamation marks. Numbers in tabular figures, each with its base. Orange is only the logo. This prompt covers the balance, the usage and the warnings. Top-ups, the card and invoices come in the next prompt: leave a quiet empty space for them under this content.

## What changes
- Remove the old plan block ("Free", "Paid", "Upgrade", allowance bars). There is one subscription: $299 a month, which includes $299 of usage. Usage above that draws from a prepaid balance.
- Remove "judge checks" and "free with your own model key". Judging is included in the price.
- The balance and all usage are shown in dollars. Remove the word "credits" and any conversion.

## 1. Included usage and balance
Two figures side by side at the top, for the whole agency:
- "Included this month": "$86.40 of $299 left", with one thin bar and the muted line "Resets 1 Dec".
- "Balance": "$412.50", with the muted line "Used after your included amount. Never expires."
Under them one line: "Lasts about 3 weeks at your current rate". When there is not enough usage to tell, the line is absent.

## 2. This month
A period picker at the right: This month, Last month, Last 30 days.
- A large "$187.40" with "used this month".
- One thin bar split by what used it, with a small legend:
  - Calls observed: "2,140 min · $64.20"
  - Text simulations: "6,160 messages · $123.20"
- Voice simulations appear as a third part only once they exist.

## 3. By workspace
A simple table, sorted by cost, so the agency can bill each client:
Workspace · Calls observed · Simulated messages · Cost
- "Bright Dental · 620 min · 1,840 · $55.40"
- A row expands in place to the workspace's agents, with the same columns.
- A total row at the bottom.
- A quiet "Download CSV" at the top right of the table.

## 4. What moved it most
Up to three plain lines under the table, each with its cost:
- "Full test run on Car service booking, 19 Nov · 486 messages · $9.72"
- "Bright Dental's calls · 620 min · $18.60"
Hidden when there is nothing to show.

## 5. How it's priced
A small quiet table:
- Subscription: $299 a month, includes $299 of usage
- Real call observed: $0.03 per minute, rounded up per call
- Text simulation: $0.02 per simulated caller message, judging included
- One muted line: "Your voice platform bills the agent's own replies in tests on your account with them."

## 6. When the balance runs low or out
- Low: when it will last less than about a week, the sidebar's profile area shows one small line, "Balance low · 3 days left", linking to Billing. Hidden otherwise.
- Out: when the included amount and the balance are both used up, everything pauses: calls are no longer recorded or checked, and tests cannot run. The balance never goes below zero. It shows in the critical colour, and a thin stripe at the top of the app, in the style of the existing app stripes, reads: "You've used this month's usage. Connexity is paused: new calls are not being checked and tests can't run." with the link "Add funds". Everything already recorded stays readable.
- Subscription unpaid: the same pause, with the stripe "Your subscription is unpaid. Connexity is paused." and the link "Update card".
- Back on: adding funds, a successful payment or the next month's included amount resumes everything by itself. The stripe disappears and no other step is needed.

## 7. Who sees it
Only Admins see Billing. A Member opening it sees one calm line: "Only Admins can see billing. Ask Alex Morgan."

## Show
- Normal state, dark, desktop, with one workspace row expanded.
- Low balance, with the sidebar line.
- Out of balance and paused, with the stripe, on Billing and on the Dashboard.
- A new agency after its first scan: balance $0.00, a muted line "Your first scan is included: 1,284 calls checked" (when the limit was reached: "Your first scan is included: the latest 2,000 calls of 3,410 checked"), "No usage yet" in place of the bar and table, and a calm stripe at the top of the app: "Your first scan is done. Start your subscription to keep checking new calls and run tests." with the link "Start subscription". This stripe is not in the critical colour.
- The Member view.
- Normal state in light, and at phone width with the table folded to Workspace and Cost.

## Avoid
- More than one plan, tiers, seats, a free allowance or "Upgrade".
- Credits or any unit that needs converting to dollars.
- Showing Connexity's own model costs or any margin.
- Charts beyond the one thin bar.
- Real client names: use Bright Dental, Car service booking and invented numbers.
```
