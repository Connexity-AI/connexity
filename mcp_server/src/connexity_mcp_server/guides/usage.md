# Usage and list prices

Connexity counts what a workspace uses and shows what it comes to at list price.
**Nothing is billed.** `get_usage` is how you answer "what does this cost".

## What is counted

| Meter | One unit | List price |
|---|---|---|
| Observed minutes | A minute of a real call, each started minute counted whole | $0.03 |
| Simulated caller messages | A message the simulated caller sent in a test run | $0.02 |
| Voice simulation minutes | A minute of a voice simulation (not available yet) | $0.25 |

- **Observed minutes** come from real calls that have ended. A 95-second call is 2
  minutes. A simulated call is never observed minutes.
- **Simulated caller messages** include the judge in their price. Messages in a
  simulated call that later stopped with an error count too.
- **The agent's replies are not counted.** The voice platform bills them on the team's
  own account.
- **Test calls made on the voice platform** are not told from real calls yet, so they
  count as real.

## Reading it

- `get_usage` answers a calendar month in UTC (this month, or `month` as YYYY-MM), or
  the last 7 or 30 days (`period`).
- `lines` are the workspace's totals per meter; `agents` the same per agent; `runs`
  each test run with its caller messages and cost, most expensive first.
- `movers` are the three things that added most: a run, or one agent's real calls on
  a day.
- Always say "at list price" with a dollar figure, and give the units next to it.

## Before a run

`run_scenarios` says the price per caller message and what the last run of the same
scenarios came to. `get_test_runs` shows each run's caller messages and cost.

## The subscription

Where paying is set up, the answer has `subscription`: the agency's one subscription,
$299 a month, which includes $299 of usage.

- `state`: `none` (not started), `active`, `past_due` (a renewal payment failed and is
  being tried again; Connexity keeps working), `unpaid`, or `ended`.
- `period_end`: when it renews. With `ends_at_period_end` it was cancelled and ends
  then instead.

You only read it. You never start, pay, cancel, resume or change a subscription, and
you never ask for or handle card details. An Admin does all of that in Agency settings,
Billing, on the payment provider's own pages. When the person asks for any of it, tell
them where.
