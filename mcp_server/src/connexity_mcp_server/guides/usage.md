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

## What is left, and the pause

Where paying is set up, the answer has `money`, in dollars:

- Each period of the subscription includes $299 of usage (`included_usd`,
  `included_left_usd`; restored at `period_end`).
- Usage beyond it draws from the prepaid `balance_usd`, which never goes below zero.
- Usage is charged in the period Connexity recorded it. An agency's first scan, made
  before it has a subscription, is never charged (`first_scan`: how many calls it read,
  of how many the last 30 days held).
- `days_left`: about how long what is left lasts at the rate of the last 7 days.

`state` says what the agency may do:

| `state` | Meaning |
|---|---|
| `first_scan` | No subscription yet; the included first scan may run |
| `needs_subscription` | No subscription and the first scan is done: paused |
| `active` | Everything runs |
| `low` | Running, with less than about a week left |
| `out` | The included amount and the balance are used up: paused |
| `unpaid` | The subscription is unpaid: paused |

While paused, new calls are not recorded or checked and tests cannot run. `add_agents`,
`scan_calls` and `run_scenarios` are refused and say so. Calls made during a pause are
never brought in afterwards. Everything already recorded stays readable, so reading
tools keep working.

Tell the person plainly that Connexity is paused and why. You cannot resume it: an
Admin starts the subscription or updates the card in Agency settings, Billing, and it
resumes by itself.

## Billing each client

When the person you act for is an admin, call `get_usage` with `agency` set to true.
The answer adds `agency_usage`: every workspace of the agency with its observed
minutes, simulated messages and cost, each split by agent, for one period
(`agency_period`: `this`, `last` or `30d`).

It counts differently from the rest of the answer, on purpose:

| | The workspace part | `agency_usage` |
|---|---|---|
| Period | A calendar month, or 7 or 30 days | The subscription's period, or 30 days |
| A call counts in | The period it happened in | The period Connexity recorded it in |

`agency_usage` is what came off the included amount and the balance, so use it for what
to bill a client and for "where did the money go". A deleted workspace keeps its line.
A member's assistant is refused: only admins see billing.
