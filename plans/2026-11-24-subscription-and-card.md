# Subscription and card

- **Owner:** Dmytro
- **Slice:** Subscription and card (roadmap Order 102.5). Built before "Balance, included
  usage and pause" (Order 102.4): Dmytro chose on 2026-11-24 to have a way to pay
  before anything can pause.
- **Design:** the prompt in the roadmap row (2026-11-23): The model, Subscription,
  Payment method, Billing details. The export Dmytro handed over on 2026-11-24 holds
  `Connexity Billing` and the `billing` section of `Connexity Agency`; they are copied
  into `designs/screens/` with this change and the prompt becomes
  `designs/20-billing-payments.md`. The build shows only the parts of that page this
  row makes work.
- **MCP:** `get_usage` also answers the agency's subscription: its state and renewal
  date. No tool pays, starts, cancels or changes anything. Contract entry updated.
- **Status:** Approved by Dmytro ("approve", 2026-11-24).

## Goal

An Admin starts the agency's subscription ($299 a month, which includes $299 of usage),
sees when it renews, changes the card and billing details, cancels and resumes. Card
details are entered only on Stripe's pages. Connexity always knows the subscription's
true state, also when Stripe's messages arrive twice or out of order.

Nothing pauses yet and no usage is charged: that is the next row, which reads the state
this one keeps.

## What the code is today

- **No payment provider, no subscription, no customer.** An agency is a name with
  people and workspaces.
- **Agency settings has Members and Workspaces.** Billing is in the design only.
- **Outside services are optional by setting:** Google sign-in and email appear only
  when their settings exist. Stripe follows the same pattern.

## Changes

### What a person sees (as designed)

- **Agency settings › Billing,** a third section, for Admins. A Member sees one line:
  "Only Admins can see billing. Ask Alex Morgan."
- **Subscription card:**
  - Not started: "Start your subscription", "$299 a month, includes $299 of usage", and
    the primary button "Start subscription", which opens Stripe's page.
  - Active: "Connexity · $299 a month", "Includes $299 of usage · Renews 1 Dec", and a
    quiet "Cancel subscription".
  - Cancelled: "Active until 1 Dec", with "Resume subscription".
  - Cancel dialog: "Cancel your subscription?" with "Keep subscription" and "Cancel
    subscription". Its sentence about the balance is left out until a balance exists.
- **Payment method:** "Visa ending 4242 · expires 08/28" with "Change"; without a card,
  "No card on file" and "Add card". Both open Stripe's page.
- **Billing details:** company name, address and tax ID, with "Edit", which opens
  Stripe's page.
- **Coming back from Stripe:** paid, "Your subscription has started."; left without
  paying, nothing changes and no error shows.
- **Not shown,** because nothing behind them works yet: the balance and usage figures,
  Add funds, auto top-up, invoices, the stripes.

### Backend

- **On the agency:** the Stripe customer, and the subscription as Connexity knows it:
  state (`none`, `active`, `past_due`, `unpaid`, `cancelled`), the current period's
  start and end, and whether it ends at the period's end.
- **Starting:** a route makes a Stripe Checkout session for the one price, with
  automatic tax and the billing address and tax ID collected, and answers its address. The customer is made once per agency, with the agency's name.
- **Card and billing details:** a route answers the address of Stripe's customer
  portal. The card's brand, last four digits and expiry, and the billing details, are
  read from Stripe when Billing opens. Connexity stores none of them.
- **Cancel and resume:** routes that tell Stripe to end the subscription at the end of
  the paid period, or to keep it.
- **Stripe's messages** (`POST /webhooks/stripe`): the signature is checked; each
  message is recorded by its id, so a repeat does nothing; the subscription is then
  read again from Stripe and stored, so the order in which messages arrive does not
  matter.
- **Settings:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`.
  Without them there is no Billing section and the routes answer 404.
- **Who:** Admins of the agency only, on every route.

### Assistants

- **`get_usage`** gains `subscription`: the state, the price, the renewal or end date.
  Rule in the answer: the assistant never starts, pays, cancels or changes a
  subscription; it sends the person to Agency settings › Billing.

### Docs

- New `docs-internal/billing.md`; `data-model.md`, `agency.md`, `decisions.md`,
  `mcp-architecture.md`, `.env.example`, `designs/README.md`.

## Decisions

- **Decided (Dmytro, 2026-11-20 and 2026-11-23, roadmap row):** hosted Connexity is paid
  only; one subscription of $299 a month that includes $299 of usage; no seats, no
  tiers; Stripe; card details only on Stripe's pages; only Admins; the assistant reads
  and never pays.
- **Decided (Dmytro, 2026-11-24):** this row is built before the balance and pause.
- **Decided (Dmytro, 2026-11-24):** cancelling runs to the end of the paid period, with
  no refund, and can be undone with "Resume subscription" until then.
- **Decided (Dmytro, 2026-11-24):** a failed renewal counts as unpaid only when Stripe
  stops retrying. Until then the state is `past_due` and Connexity keeps working.
- **Decided (Dmytro, 2026-11-24):** Stripe Tax is on from the start: Checkout adds tax
  by the customer's location and collects the billing address and tax ID.
- **Decided (Dmytro, 2026-11-24):** Dmytro adds Stripe test keys to the git-ignored
  `.env`, and the flow is played through in Stripe's test mode.
- **Proposed:** Stripe is called over plain HTTP like every other outside service here,
  so its calls are tested for a timeout, an empty answer and a malformed one.

## Done when

- Through the API on the local database, with Stripe faked: starting answers a Checkout
  address for the right price and customer; a message that the subscription is active
  sets the state and period; the same message again changes nothing; an older message
  arriving late does not move the state back; a failed renewal and a cancellation set
  their states; cancel and resume call Stripe and are reflected; a message with a wrong
  signature is refused; a Member and an assistant are refused on every route; without
  Stripe settings the routes answer 404.
- `get_usage` answers the subscription for an assistant; MCP server tests pass.
- Frontend types and lint pass; the full `make check` passes.
- With Stripe test keys from Dmytro: one real start, card change, cancel and resume in
  Stripe's test mode, played through and written into the Outcome.

## Out of scope

- **Dmytro's, needed before this works in production:** the Stripe account for
  Connexity; his tax registrations entered in Stripe Tax, without which Stripe adds no
  tax; the product and its $299 monthly price; the customer portal switched on
  with card and billing details editable; the webhook endpoint registered for the
  backend's address; live keys put into Secret Manager and Cloud Run. The plan's Outcome
  will list the exact values.
- Pausing, the included amount and the balance (row "Balance, included usage and
  pause"); top-ups, auto top-up, invoices, failed-payment stripe and emails (row
  "Top-ups, invoices and payment emails"); usage on the Billing page.
- Refunds, coupons, more than one price, annual billing.

## Risks

- **A subscription can be paid while Connexity thinks it is not,** if messages are
  missed. Reading the subscription from Stripe on every message, and again when Billing
  opens, bounds that.
- **This row takes money before anything depends on it.** Until the pause exists, a
  subscription changes nothing an agency can do; the page says what it includes and
  nothing more.

## Outcome

### Deviations from the plan

- **The cancel dialog's sentence is different.** The design says "Connexity keeps
  working until 1 Dec, then pauses. Your balance of $412.50 stays…". Neither a pause
  nor a balance exists yet, so it says "Your subscription stays active until 1 Dec and
  is not renewed. You can resume it before then."
- **A failed renewal has a line on the subscription card:** "A renewal payment failed
  and is being tried again. Update your card.", and for unpaid "Your subscription is
  unpaid. Update your card." The designed failed-payment line and stripe belong to the
  top-ups row; without any line the state would be invisible.
- **When Stripe cannot be reached,** Billing shows the last known subscription and the
  line "Payment details can't be shown right now. Try again in a minute." Not in the
  design.
- **Under the card and billing details** one muted line says they are entered on the
  payment provider's page. Not in the design; it is the rule of the row.
- **Coming back from Stripe before the payment is known:** "Your payment is processing.
  This page updates when it's done."
- **`AgencyDetail` gained `billing`:** whether paying is set up, so the web app knows
  whether to show the Billing section.
- **`STRIPE_AUTOMATIC_TAX`,** a fourth setting, on by default. Stripe refuses to start
  Checkout with automatic tax until the head office address is entered in Stripe, so a
  developer's sandbox can turn it off.
- **A state `ended`** instead of the plan's `cancelled`: "cancelled" in the design means
  still active until the period's end, which is `active` with the ending flag.
- **A message about a customer Connexity does not know** is answered as ignored and
  remembered, not refused.

### Check results

| What | Result |
|---|---|
| `test_billing.py` (30 tests), Stripe faked with `respx`: starting makes one customer and a Checkout for the one price, with automatic tax, tax ID and address collection, and the right return addresses; a second start closes the first one's unpaid Checkout page; a start with a running subscription is refused; an unfinished attempt does not hide a paid subscription; a message sets the state and period and a repeat does nothing; a late older message does not move the state back; each Stripe status becomes the right state, also the two ways Stripe marks "ends at the period's end"; a running subscription wins over an ended one; a wrong secret, an old timestamp and a missing signature are refused; an unknown customer is ignored; when Stripe cannot be read the message is not marked handled and works on the next try; Billing reads the subscription, card and details; with Stripe down it shows the last known state; before any payment it asks Stripe nothing; cancel and resume send the right change; the portal link needs a customer; a Member, an outsider, nobody and an assistant are refused on every route; without Stripe settings every route and the webhook answer 404; the assistant's `get_usage` carries the subscription, and nothing where paying is not set up; a timeout, an empty answer, HTML, a list, a missing field, an unknown status and a refusal each raise one error; the older place for a subscription's period is read too | passed |
| Usage, agency and schema tests | passed |
| MCP server tests (67), with the subscription on `get_usage` | passed |
| Backend `ruff` and `pyright`; frontend types, lint and formatting; client regenerated | passed |
| Full `make check`, after the review fixes | passed, every step. The billing, agency, usage, invite and deletion tests were also run with no Stripe settings, as CI has none: passed |

**Played through against Stripe's sandbox** with the key Dmytro gave (a temporary script
through the API on the local database, deleted afterwards; the sandbox customer it made
was deleted too):

| Step | Result |
|---|---|
| Start with automatic tax on | Refused by Stripe: the sandbox has no head office address ("You must have a valid head office address to enable automatic tax calculation") |
| Start with automatic tax off | A Checkout address for the $299 price, and one Stripe customer made |
| Billing before paying | `none`, no card |
| A subscription paid with Stripe's test card, made through Stripe's API instead of typing into Checkout | Stripe: `active`; the period sits on the subscription's item, as the code expects |
| Billing after paying | `active`, the period's end one month ahead, "visa … 4242" |
| A second start | Refused (409) |
| Cancel, then Stripe asked directly | Ends at the period's end, state still `active` |
| Resume | No longer ending |
| The portal link | An address on `billing.stripe.com` |
| A real `customer.subscription.deleted` event from Stripe, signed locally and posted to the webhook | Stored; state `ended` |

A sandbox product "Connexity" and its $299 monthly price were created in Dmytro's Stripe
sandbox for this; the price id is in the git-ignored `.env`.

For Dmytro to check on screen, with the sandbox key in `.env` and
`STRIPE_AUTOMATIC_TAX=false` until the head office address is in Stripe (dark, light and
phone width, against `designs/screens/Connexity Billing.dc.html`):

1. Agency settings has Billing between Members and Workspaces. As a Member: "Only Admins
   can see billing. Ask …".
2. Not started: "Start your subscription", "$299 a month, includes $299 of usage",
   "Start subscription" opens Stripe's page.
3. Pay there with Stripe's test card 4242 4242 4242 4242: back on Billing, "Your
   subscription has started.", "Connexity · $299 a month", "Includes $299 of usage ·
   Renews …", the card row and the billing details.
4. "Change" and "Edit" open Stripe's portal and return to Billing.
5. "Cancel subscription": the dialog, then "Active until …" with "Resume subscription";
   resume brings "Renews …" back.

### Code review

Two findings, both fixed:

- An agency could end up paying for two subscriptions: every click on "Start
  subscription" made a new Checkout page while earlier ones stayed payable. The
  customer's open Checkout pages are now closed before a new one is made (listing and
  closing them was checked against the sandbox).
- An unfinished first payment that was newer could hide an active subscription, so
  Billing would offer to start again. A subscription that is paid for or owed now comes
  first.

Two people clicking at the very same moment can still each get a page; closing happens
when the next page is made. Stripe has no setting that forbids a second subscription.

### Not done

- **Not verified:** Checkout was not paid in a browser (the subscription was made
  through Stripe's API with the test card), and Stripe did not deliver a message to
  this machine: the webhook was fed one real event by hand. Both happen for the first
  time on a deployed backend with the endpoint registered.
- **Automatic tax was not exercised:** the sandbox refuses it until the head office
  address is entered in Stripe.
- **Production is not set up.** `docs-internal/billing.md` lists the five things to do
  in Stripe; the live key, price id and webhook secret then go into Secret Manager and
  Cloud Run, which are Dmytro's. The live key was not stored anywhere by this change.
- The screens were not opened in a browser.
- Nothing depends on the subscription yet: no pause, no charge for usage.
