# Billing: the subscription and the card

Each agency has one subscription: $299 a month, which includes $299 of usage (Decided
by Dmytro, 2026-11-23). Stripe takes the money. Plan:
[`plans/2026-11-24-subscription-and-card.md`](../plans/2026-11-24-subscription-and-card.md).

Code: `app/services/stripe.py` (every call to Stripe), `app/crud/billing.py` (what is
stored), `app/api/routes/billing.py` (the routes), `stripe_webhook` in
`app/api/routes/webhooks.py`, and
`frontend/apps/web/src/components/agency/billing-view.tsx`.

What an agency has left, and the pause, are built on the subscription: see "What is
left" and "The pause" below
([`plans/2026-11-24-balance-and-pause.md`](../plans/2026-11-24-balance-and-pause.md),
`app/services/billing_state.py`).

## What Connexity stores and what it does not

On the agency: Stripe's customer id and subscription id, the subscription's state, the
current period's start and end, and whether it ends at the period's end. This is a copy;
Stripe stays the source of truth.

Never stored: a card number, the card's brand or last digits, the billing address, a tax
ID. The card's summary and the billing details are read from Stripe each time Billing
opens. Card details are typed only on Stripe's pages.

## States

| Connexity | Stripe | Meaning |
|---|---|---|
| `none` | no subscription, `incomplete`, `incomplete_expired` | Never started, or a first payment that did not go through |
| `active` | `active`, `trialing` | Paid |
| `past_due` | `past_due` | A renewal failed and Stripe is retrying. Connexity keeps working (Decided by Dmytro, 2026-11-24) |
| `unpaid` | `unpaid`, `paused` | Stripe stopped retrying |
| `ended` | `canceled` | Cancelled and past the end of its paid period |

Cancelling does not end a subscription at once: it runs to the end of the paid period,
with no refund, and can be resumed until then (Decided by Dmytro, 2026-11-24). While it
runs out, the state stays `active` with `subscription_ends_at_period_end` set.

When a customer has several subscriptions, one that is paid for or owed wins over an
unfinished first payment, and that over one that ended; among equals, the newest.

Starting closes every Checkout page of the customer that was opened and not paid, so
two pages cannot both start a subscription.

## Keeping the state true

The state is never taken from what a message says. Three things read the subscription
from Stripe and store it:

- **A message from Stripe** (`POST /api/v1/webhooks/stripe`). Its signature is checked
  with the endpoint's secret (HMAC-SHA256 over `timestamp.body`, at most five minutes
  old). It is handled once, by its id (`stripe_event`). Then the customer's subscription
  is read from Stripe, so a repeat or a message arriving late cannot move the state
  back. When Stripe cannot be read, the answer is an error and the message is not marked
  as handled, so Stripe sends it again.
- **Opening Billing.** A person coming back from Stripe's payment page sees the new
  state without waiting for a message.
- **Starting, cancelling and resuming**, before they act.

When Stripe cannot be reached, Billing shows the last known state without the card and
details, and says so.

## What is left

- **Included:** $299 for each period of a subscription that is active or past due. It
  does not roll over. The period is the subscription's, not the calendar month.
- **Balance:** the sum of the agency's ledger lines (`balance_entry`). A line of kind
  `added` puts money in; today only Connexity adds one, by hand
  (`backend/scripts/add_balance.py`); `top_up` and `auto_top_up` lines come from paid
  invoices (see "Adding funds"). One line of kind `usage` per
  period says what that period's usage beyond the included amount drew. It is rewritten
  whenever the state is worked out, never added to, so working it out twice changes
  nothing; it is settled once more when the period moves on.
- **Never below zero:** the usage that crosses the line is recorded and checked, and
  what it costs beyond the money left is not charged.
- **Charged when recorded:** a period's usage is the usage Connexity recorded in it
  (`usage_record.created_at`), at list price, in every workspace of the agency, deleted
  ones too. So the first scan, recorded before there is a subscription, is never
  charged, and a later scan of older calls is. The usage page counts by when a call
  happened, so the two can differ at a period's edges.

## States

Worked out in one place (`money_of`), from the subscription and what is left:

| State | When | Calls recorded, tests | First scan |
|---|---|---|---|
| `first_scan` | No subscription, and not every workspace with agents has finished its first scan (or none has agents) | No | Yes, with its limit |
| `needs_subscription` | No subscription (never started, or ended), first scan done | No | No |
| `active` | Subscription active or past due, money left | Yes | Yes |
| `low` | As `active`, and what is left lasts less than 7 days at the average of the last 7, told only from usage on at least 3 of them, and only when that comes before the period ends | Yes | Yes |
| `out` | Subscription active or past due, included amount and balance both used up, and auto top-up off or its last payment failed | No | No |
| `unpaid` | Subscription unpaid | No | No |

Nothing needs to be done to resume: a payment, a new period or an added balance changes
the state the next time it is worked out.

**Only where paying is set up.** Without Stripe's settings there is no state: nothing is
drawn, nothing pauses and no stripe shows. That is every self-hosted install, and
production until the live keys are in.

**An agency that already exists** when paying is switched on has no subscription, so it
is paused until an Admin starts one (Decided by Dmytro, 2026-11-24).

## The pause

For a paused agency:

- **The Retell webhook** stores nothing and still answers with success, so Retell does
  not send the call again.
- **The scheduled pull** passes over its calls while its position moves on.
- **The trace ingest route** answers 402.
- **The assistant's `add_agents`, `scan_calls` and `run_scenarios`** answer 402 with
  what to tell the person. Reading tools keep working.

Calls made during a pause are never brought in afterwards (Decided by Dmytro,
2026-11-24). Each pause is recorded with its start, end and reason (`billing_pause`);
nothing shows them yet.

## The included first scan

An agency with no subscription gets its first scan without paying (Decided by Dmytro,
2026-11-24): the last 30 days, the latest 100 calls per agent, at most 500 calls per
agency, and one included scan per voice platform account (`included_scan`, by the key's
fingerprint: another agency connecting the same account gets none). `agent.scan_total`
is what the scan reads and `agent.scan_window_total` what the 30 days held when the
limit cut it. A subscribed agency's scans have no limit and are charged like any usage.

## Adding funds

An Admin of an agency with a subscription adds $50 to $10,000 to the balance
(`app/services/top_up.py`, `components/agency/billing-payments.tsx`).

- **By hand:** "Add funds" opens a Stripe Checkout page for a one-time payment, and
  Stripe makes an invoice for it, marked `top_up`.
- **Auto top-up:** the setting is on the agency (on or off, and the amount). The
  scheduled run (every minute, with the call pull) looks at every agency that has it
  on: when the period's included amount and the balance are both used up (Decided by
  Dmytro, 2026-11-24) it makes an invoice marked `auto_top_up` and has Stripe charge
  the saved card. While there is money left it asks Stripe nothing. An agency with it
  on is not paused in the minute between running out and the charge, so no call is
  lost in between; what it uses then comes off the top-up. Only one run can take an
  agency's turn, so two runs that overlap cannot both charge. The invoice's id is kept on the
  agency before the card is charged, so a run that dies in between is finished by the
  next one and never charges twice. There is no limit on how often it may charge
  (Decided by Dmytro, 2026-11-24): with usage that uses up each top-up within the
  minute, that is up to one charge a minute.
- **Crediting:** a paid invoice marked as a top-up adds one ledger line for its amount
  before tax. The line carries the invoice's id and the database allows one line per
  invoice, so a payment is credited once however often it is reported. Three things
  credit it, whichever comes first: Stripe's message, the person coming back from
  Stripe's page, and opening Billing.
- **A failed automatic payment** voids its invoice (so Stripe cannot charge it later by
  itself) and is recorded on the agency with Stripe's reason and the card that failed.
  Nothing is charged again until the card is a different one or auto top-up is switched
  off and on. Billing shows a line, the app a warning stripe, and the Admins get one
  email.

The part of a call's cost that went beyond the money left is not charged at the time.
If funds are added later in the same period it is drawn then, because a period's line
is always worked out from the whole period.

## Invoices

Read from Stripe when Billing opens and never stored: date, "Subscription", "Added
funds" or "Auto top-up", the total with tax, a status (paid; processing for one still
open; failed for one voided or uncollectible) and the link to Stripe's page with the
PDF. Drafts are left out.

## Emails

Sent by the scheduled run to every Admin of the agency
(`app/services/billing_notify.py`), each once per stretch of its state:

| Email | When |
|---|---|
| "Your Connexity balance is low" | The state becomes `low`, unless auto top-up is on |
| "A Connexity payment failed" | An automatic payment fails |
| "Connexity is paused" | The state becomes `out` or `unpaid` |

A state that begins and ends between two runs sends nothing. An agency that never
subscribed gets none of them.

## Usage on Billing

Agency settings › Billing shows, for Admins, what is left (the included amount with its
reset date, the balance, about how long it lasts) and what was used in a period: the
total, the split by kind, each workspace with its agents, the three things that added
most, the prices, and a CSV to bill each client from
(`app/services/billing_usage.py`, `components/agency/billing-usage.tsx`).

- **Periods** are the subscription's: "This period", "Last period" (the month before
  the current one's start) and "Last 30 days". Without a subscription only the last 30
  days exist (Decided by Dmytro, 2026-11-24).
- **Same basis as the money:** usage is counted by when Connexity recorded it, in every
  workspace of the agency, deleted ones too (shown as "Deleted"). "This period" is
  exactly what came off the included amount and the balance; a test checks it.
- **Only what was charged.** Usage recorded before the agency's first subscription
  began (`agency.first_subscribed_at`), which is the included first scan, is left out of
  every figure, the CSV and the assistant's `agency_usage`. An agency that never
  subscribed sees "No usage yet". Where paying is not set up nothing is charged and
  everything is shown.
- **List price only.** Neither route reads Connexity's own cost, tokens or model names.
- **The CSV** has one row per workspace and agent and a total row. A name that starts
  like a formula is written so a spreadsheet does not run it.

The assistant's per-workspace usage (`get_usage` without `agency`) still counts by
calendar month and by when a call happened; `docs-internal/usage.md` describes it.

## Screens

- **The stripe** at the top of the app (`components/shell/billing-stripe.tsx`,
  `designs/screens/Connexity Readiness Bar.dc.html`), for `needs_subscription`, `out`
  and `unpaid`, and in the warning colour for a failed automatic payment while the
  balance is above zero. The `out` stripe ends with "Add funds".
- **The sidebar line** "Balance low · 3 days left", for `low`.

Both read `GET /api/v1/agencies/{id}/billing/status`, which anyone in the agency may
call and which answers null where paying is not set up.

## Routes

All for Admins of the agency; a Member gets "Only Admins can see billing. Ask …". No
route takes an assistant's token.

| Route | What |
|---|---|
| `GET /api/v1/agencies/{id}/billing` | The subscription, the card's summary and the billing details |
| `POST /api/v1/agencies/{id}/billing/checkout` | The address of Stripe's page that starts the subscription. Makes the Stripe customer the first time. Refused when a subscription is running |
| `POST /api/v1/agencies/{id}/billing/portal` | The address of Stripe's page for the card and billing details |
| `POST /api/v1/agencies/{id}/billing/cancel` | Cancel at the end of the paid period |
| `POST /api/v1/agencies/{id}/billing/resume` | Undo a cancellation |
| `POST /api/v1/webhooks/stripe` | Stripe's messages |
| `GET /api/v1/agencies/{id}/billing/status` | Anyone in the agency: what is left and the state, for the stripe and the sidebar |
| `POST /api/v1/agencies/{id}/billing/top-up` | Admins: the address of Stripe's page to add an amount |
| `POST /api/v1/agencies/{id}/billing/top-up/confirm` | Admins: what became of a top-up they came back from; credits it if not yet credited |
| `PUT /api/v1/agencies/{id}/billing/auto-top-up` | Admins: switch auto top-up and set its amounts; needs a card on file |
| `GET /api/v1/agencies/{id}/billing/usage?period=` | Admins: the period's usage per workspace and agent, at list price |
| `GET /api/v1/agencies/{id}/billing/usage.csv?period=` | Admins: the same as a CSV |

## The assistant

`get_usage` answers `subscription` (state, price, included amount, period end, whether
it ends then) where paying is set up. It also answers `money`: what is left of the
included amount and the balance, the state, and about how many days it lasts. With
`agency` set, an Admin's assistant also gets `agency_usage`, the same figures as the
Billing page, to bill each client from. The assistant never starts, pays, cancels or
changes a subscription and never handles card details.

## Settings

| Setting | What |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe's secret key. A sandbox key (`sk_test_…`) on a developer's machine, the live key only in production |
| `STRIPE_PRICE_ID` | The $299 monthly price |
| `STRIPE_WEBHOOK_SECRET` | The signing secret of the webhook endpoint (`whsec_…`). Without it messages are refused |
| `SALES_CONTACT_URL` | Where "Talk to us about volume pricing" leads. Without it the line is not shown, so a self-hosted install does not link to Connexity's calendar |
| `STRIPE_AUTOMATIC_TAX` | On by default (Decided by Dmytro, 2026-11-24): Checkout adds tax through Stripe Tax. Stripe refuses to start Checkout until the head office address and tax registrations are entered in Stripe |

Without the key and the price there is no Billing section and every route answers 404.

## In Stripe, before production

These are set in Stripe's dashboard, not in code:

1. The product and its $299 monthly price; its id goes into `STRIPE_PRICE_ID`.
2. Stripe Tax: the head office address and the tax registrations.
3. The customer portal switched on, with the payment method and billing details
   editable. Cancelling is done in Connexity, so it can stay off in the portal.
4. A webhook endpoint at `<backend>/api/v1/webhooks/stripe` for the events
   `customer.subscription.created`, `customer.subscription.updated`,
   `customer.subscription.deleted`, `checkout.session.completed`, `invoice.paid` and
   `invoice.payment_failed`; its
   signing secret goes into `STRIPE_WEBHOOK_SECRET`.
5. Under Billing, what happens when all retries of a renewal fail: "mark the
   subscription as unpaid" (or cancel it). If it is left as past due, an agency that
   never pays stays `past_due` and Connexity never counts it as unpaid.
