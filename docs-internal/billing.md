# Billing: the subscription and the card

Each agency has one subscription: $299 a month, which includes $299 of usage (Decided
by Dmytro, 2026-11-23). Stripe takes the money. Plan:
[`plans/2026-11-24-subscription-and-card.md`](../plans/2026-11-24-subscription-and-card.md).

Code: `app/services/stripe.py` (every call to Stripe), `app/crud/billing.py` (what is
stored), `app/api/routes/billing.py` (the routes), `stripe_webhook` in
`app/api/routes/webhooks.py`, and
`frontend/apps/web/src/components/agency/billing-view.tsx`.

**Nothing depends on the subscription yet.** No usage is charged and nothing pauses;
that is the roadmap row "Balance, included usage and pause", which reads the state kept
here.

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

## The assistant

`get_usage` answers `subscription` (state, price, included amount, period end, whether
it ends then) where paying is set up. The assistant never starts, pays, cancels or
changes a subscription and never handles card details.

## Settings

| Setting | What |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe's secret key. A sandbox key (`sk_test_…`) on a developer's machine, the live key only in production |
| `STRIPE_PRICE_ID` | The $299 monthly price |
| `STRIPE_WEBHOOK_SECRET` | The signing secret of the webhook endpoint (`whsec_…`). Without it messages are refused |
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
   `customer.subscription.deleted`, `invoice.paid` and `invoice.payment_failed`; its
   signing secret goes into `STRIPE_WEBHOOK_SECRET`.
5. Under Billing, what happens when all retries of a renewal fail: "mark the
   subscription as unpaid" (or cancel it). If it is left as past due, an agency that
   never pays stays `past_due` and Connexity never counts it as unpaid.
