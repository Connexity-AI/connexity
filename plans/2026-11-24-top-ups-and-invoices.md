# Top-ups, invoices and payment emails

- **Owner:** Dmytro
- **Slice:** Top-ups, invoices and payment emails (roadmap Order 102.55), one pull
  request (Decided by Dmytro, 2026-11-24).
- **Design:** `designs/20-billing-payments.md`, sections 1 Add funds, 2 Auto top-up, 5
  Invoices, 6 When a payment fails, 7 Emails and 8 Large volumes, with the screens in
  `designs/screens/Connexity Billing.dc.html` (4a to 8d), the `low`, `failed` and
  `paused` variants of `Connexity Email`, and the failed-payment stripe in `Connexity
  Readiness Bar`. All are in the repo; the design does not change.
- **MCP:** `get_usage` with `agency` also answers the latest invoices and the auto
  top-up setting for an Admin's assistant. No tool pays, adds funds or changes the
  setting. Contract entry updated.
- **Status:** Approved by Dmytro ("Accept, build", 2026-11-24).

## Goal

An Admin adds money to the agency's balance through Stripe and sees it arrive, so an
agency that used up its included $299 can keep running without waiting for the next
period. The same Admin sees every invoice (subscription and added funds) and downloads
it. With auto top-up on, the card is charged before the balance runs out, so Connexity
does not pause. When a payment fails, or the balance runs low or out, the agency's
Admins are told on screen and by email.

## What the code is today

- **The balance is a ledger** per agency, and only Connexity can add to it, by a script
  (pull request 266).
- **Stripe is used for the subscription only:** Checkout to start, the portal for the
  card, messages checked and replayed safely (pull request 265).
- **The paused stripe for "out" has no link,** and says when the next period starts.

## Changes

### What a person sees (as designed)

- **"Add funds"** next to the Balance, the page's primary button, shown once there is a
  subscription (while "Start subscription" is showing it is hidden).
- **The dialog:** three amounts as tiles ($100, $500, $2,000, with $500 picked) and
  "Other amount" (minimum $50); "About 5 weeks at your current rate" for the picked
  amount, absent when it cannot be told; "Plus tax where it applies. Added funds never
  expire and are non-refundable."; "Continue to payment" opens Stripe's page.
- **Coming back:** paid, "$500.00 added to your balance" and the new balance; left
  without paying, nothing changes and no error; not confirmed yet, "Your payment is
  processing. The balance updates when it's done."
- **Invoices:** Date, Description, Amount, Status and a download link, newest first:
  "Subscription", "Added funds". Status is Paid, Processing or Failed. Five, then "Show
  all". Empty: "No invoices yet."
- **Auto top-up:** a card with a switch under the usage summary: "Keeps Connexity
  running by adding funds before your balance runs out." On, one sentence with two
  small fields: "When the balance falls below $50, add $200." Off, "Without it,
  Connexity pauses when your balance reaches $0." Turning it on with no card on file
  opens Stripe's page to add one.
- **When a payment fails:** on Billing, a line in the critical colour above the
  balance, "Your auto top-up of $200 failed: the card was declined." with "Update
  card"; at the top of the app a stripe in the warning colour, "A payment failed.
  Update your card before your balance runs out." Once the balance reaches $0 the
  paused stripe replaces it.
- **A card about to expire** shows a warning line on the payment method row.
- **Large volumes:** one muted line at the bottom, "Running a large fleet? Talk to us
  about volume pricing." It is shown only where the deployment names where "Talk to
  us" leads.
- **The paused stripe** for "out" ends with "Add funds", which opens Billing.
- **Three emails** to the agency's Admins, each with one button: "Your Connexity
  balance is low" (the balance, about how long it lasts, "Add funds"), "A Connexity
  payment failed" (the amount, the reason, "Update card"), "Connexity is paused" ("Add
  funds").

### Backend

- **Starting a top-up:** a route makes a Stripe Checkout page for a one-time payment of
  the chosen amount, on the agency's Stripe customer, with tax as for the subscription,
  and asks Stripe to make an invoice for it. Amounts from $50 to $10,000.
- **Crediting the balance:** when Stripe says the top-up's invoice is paid, one ledger
  line of a new kind, `top_up`, is added for the amount before tax. It is tied to the
  invoice's id, so a repeated message or a reload cannot add it twice. It is credited
  the same way when the person comes back from Stripe before the message arrives.
- **Invoices:** read from Stripe when Billing opens (date, what it was for, total,
  status, the link to Stripe's PDF). Connexity stores none of them.
- **Resuming:** an agency paused for "out" runs again as soon as the line is added;
  nothing else is needed.
- **Auto top-up:** the setting (on or off, the amount; the threshold was dropped, see
  Outcome) is kept on the agency. The scheduled run that already pulls calls also looks at every agency with
  it on: when the balance is below the threshold and no automatic payment is waiting,
  it makes an invoice for the amount on the agency's Stripe customer and has Stripe
  charge the saved card. The balance is credited by the same path as a top-up by hand.
  There is no limit on how often this may happen (Decided by Dmytro, 2026-11-24).
- **A failed automatic payment** is recorded with Stripe's reason. No new attempt is
  made until the card changes or an Admin turns auto top-up off and on again, so a dead
  card is not charged again and again.
- **The emails** are sent once per event: when the state first becomes low (not while
  auto top-up is on), when a payment fails, and when the agency becomes paused for
  "out" or "unpaid". A marker on the agency keeps each from being sent twice for the
  same event.
- **`SALES_CONTACT_URL`:** where "Talk to us" leads. Without it the line is absent, so
  a self-hosted install does not link to Connexity's calendar. Dmytro's address goes
  into production's settings, not into the public repo.

### Assistants

- **`get_usage` with `agency`:** the latest invoices (date, what for, amount, status)
  and the auto top-up setting, for an Admin's assistant. Rules: it never pays, adds
  funds, changes auto top-up or asks for card details; an Admin does that in Agency
  settings › Billing.

### Docs

- `docs-internal/billing.md` (top-ups, invoices), `data-model.md`, `decisions.md`,
  `mcp-architecture.md`.

## Decisions

- **Decided (Dmytro, 2026-11-23, roadmap row):** add funds through Stripe in $100, $500,
  $2,000 or another amount, minimum $50; unused balance is not refunded and never
  expires, and the dialog says so; the assistant reads and never pays.
- **Decided (Dmytro, 2026-11-24):** Stripe Tax is on, as for the subscription.
- **Proposed:** the balance is credited with the amount before tax.
- **Proposed:** the most one top-up can add is $10,000.
- **Proposed:** invoices are read from Stripe each time and not stored.
- **Decided (Dmytro, 2026-11-24):** one pull request for the whole row.
- **Decided (Dmytro, 2026-11-24):** no limit on how often auto top-up may charge.
- **Decided (Dmytro, 2026-11-24):** "Talk to us" leads to Dmytro's meeting page.
- **Proposed:** that address is a deployment setting, not written into the public repo.
- **Proposed:** auto top-up accepts a threshold from $10 and an amount from $50 to
  $10,000.
- **Proposed:** after a failed automatic payment nothing is charged again until the
  card changes or auto top-up is switched off and on.
- **Proposed:** the three emails go to every Admin of the agency, and the low-balance
  email is not sent while auto top-up is on.

## Done when

- Through the API on the local database, with Stripe faked: starting a top-up answers a
  Checkout address for the right amount, customer and tax, and refuses under $50, over
  $10,000 and without a subscription; a paid invoice's message adds one ledger line
  for the amount before tax and a repeat adds none; coming back before the message
  credits it once; an agency paused for "out" runs again after it; invoices list in the
  right order with their status and link; a Member, an outsider and an assistant are
  refused; without Stripe settings the routes answer 404.
- Auto top-up: with it on and the balance under the threshold, the scheduled run makes
  one invoice for the amount and has it charged, and makes no second one while that is
  waiting; a paid one credits the balance; a failed one is recorded with its reason,
  shows on Billing and in the stripe, sends one email, and is not tried again until
  the card changes; with it off nothing is charged.
- Each of the three emails is sent once per event, to every Admin, with the designed
  subject and sentence.
- With the sandbox key: one real top-up paid with Stripe's test card, the balance
  credited from Stripe's real invoice, and the invoice listed, written into the
  Outcome.
- MCP server tests pass; frontend types and lint pass; the full `make check` passes.

## Out of scope

- Refunds, credit notes, promo codes, paying by bank transfer.
- **Dmytro's, in Stripe before production:** the webhook endpoint must also send
  `invoice.paid` (already listed in `docs-internal/billing.md`).

## Risks

- **Money taken and not credited** is the failure that matters. The credit is tied to
  Stripe's invoice id, made on the message and again when the person returns, and
  Billing reads Stripe each time it opens, so a missed message is caught there.
- **Money credited twice** is prevented by one ledger line per invoice id, enforced by
  the database.
- **Auto top-up charges a card with nobody present, without a limit,** by decision. A
  runaway test loop with it on keeps charging. The scheduled run fires every minute and
  makes at most one charge per agency each time, so that is up to 60 charges an hour,
  each of the chosen amount. The setting's sentence and the invoice for every charge
  are what the agency sees.
- **This is the largest change of the billing rows in one pull request.** The review
  and the sandbox play-through cover each part separately.

## Outcome

### Deviations from the plan

- **Auto top-up has no threshold** (Decided by Dmytro during the review, 2026-11-24:
  "we should make auto top up only when it reaches 0 both in balance and in credits").
  The plan and the design say "When the balance falls below $50, add $200." It now
  charges only when the period's included amount and the balance are both used up, and
  the sentence reads "When your included usage and balance run out, add $200." The
  setting is on or off and one amount. **The design still shows the old sentence with
  two fields and needs updating.**
- **With auto top-up on, running out does not pause the agency** until a payment
  fails. Otherwise every top-up would begin with up to a minute in which calls are not
  recorded and never brought in. What is used in that minute comes off the top-up.

- **A third way to credit a top-up:** opening Billing credits any paid top-up invoice
  that was not credited yet, beside Stripe's message and the return from Stripe. A
  missed message then costs nothing.
- **A failed automatic payment voids its invoice,** so Stripe cannot charge it later by
  itself. It shows in the invoice list as "Failed".
- **"No card on file" counts as a failed payment** when auto top-up is on and the card
  was removed: recorded, told once, held until a card exists.
- **Turning auto top-up on with no card** opens Stripe's page from the screen; the
  route itself answers "Add a card first."
- **The amounts in the auto top-up sentence are saved with a "Save" button** that
  appears when they change; the design shows the fields only.
- **The "paused" email has a second wording** for an unpaid subscription ("Update your
  card and it resumes by itself.", button "Update card"). The design has one, for a
  balance that ran out.
- **The low-balance email says what is left of the included amount and the balance
  together,** since both are what runs out.
- **Two more fields on the status the app reads:** whether an automatic payment
  failed (for the warning stripe), and on a card whether it expires this month or
  next.
- **The part of a call's cost beyond the money left is drawn if funds are added later
  in the same period.** The balance row's doc said it "is not charged"; with top-ups
  that is true only until money arrives. `docs-internal/billing.md` now says so.
- **`checkout.session.completed` is one more Stripe message to register** for the
  webhook, so a top-up is credited as soon as it is paid.

### Check results

| What | Result |
|---|---|
| `test_top_ups.py` (21 tests, 25 cases, with the review's), Stripe as an invented account in memory: adding funds opens Stripe's page for the amount, customer, tax and a top-up invoice, and refuses under $50, over $10,000 and without a subscription; a paid top-up is credited once, for the amount before tax, also when Stripe reports it twice; coming back from Stripe credits it before the message and never twice; an unfinished payment and another agency's payment add nothing; adding funds resumes an agency that ran out; Billing lists invoices newest first with what they were for and their status, leaves drafts out, and credits a paid top-up whose message never arrived; a card expiring this month is flagged; auto top-up charges once under the threshold and not again while there is enough; a run that died after making the invoice is finished, not repeated; a declined card voids the invoice, is recorded, emails every Admin once, is not charged again, and is charged after the card changes; nothing happens when it is off; switching it on needs a card and amounts within the limits; the low and paused emails go out once per stretch and again after money arrived and ran out; the low email is not sent while auto top-up is on; a Member and an assistant are refused and without Stripe settings the routes answer 404; an Admin's assistant reads the invoices and the setting; nothing is charged while any of the included amount is left; two runs at once charge once, and a dead run's claim is taken over; a turn with money left asks Stripe nothing; with auto top-up on running out does not pause until a payment fails; an invoice answer that cannot be read raises one error | passed |
| Billing, balance, usage and schema tests | passed |
| MCP server tests (70) | passed |
| Backend `ruff` and `pyright`; frontend types, lint and formatting; client regenerated | passed |
| Full `make check`, after the review fixes and the change to auto top-up | passed, every step |

**Played through against Stripe's sandbox** (a temporary script through the API on the
local database, deleted afterwards, as was the sandbox customer; automatic tax off
because the sandbox still has no head office address):

| Step | Result |
|---|---|
| A subscription paid with Stripe's test card | Billing lists "Subscription · $299.00 · paid" |
| "Add funds" for $500 | A Checkout address; Stripe's own record of the page: a one-time payment of 50000 cents, invoice creation on, marked `top_up` |
| Asking what became of it before anyone paid | `processing`, nothing credited |
| Auto top-up switched on (then still with a $50 threshold, see Deviations), then one run | Stripe made and charged a real invoice; balance $200.00 |
| A second run | Nothing charged: there is enough |
| Billing | "Auto top-up · $200.00 · paid" and "Subscription · $299.00 · paid", each with a link |
| Stripe's real `invoice.paid` event for that invoice, signed locally and posted to the webhook | Stored; still one ledger line |
| The card replaced by Stripe's test card that is always declined, then a run | `failed`, "Your card was declined." |
| The next run with the same card | Held: nothing charged |
| Billing | The failed payment and its reason; invoices "Auto top-up · failed", "Auto top-up · paid", "Subscription · paid" |

For Dmytro to check on screen, with the sandbox key and `STRIPE_AUTOMATIC_TAX=false` in
`.env` (dark, light and phone width, against `designs/screens/Connexity Billing.dc.html`
4a to 7b):

1. With a sandbox subscription: "Add funds" beside the Balance; the dialog with $500
   picked, "Other amount" refusing under $50, and "Continue to payment" opening
   Stripe's page.
2. Pay there with 4242 4242 4242 4242: back on Billing, "$500.00 added to your
   balance", the new balance, and "Added funds · $500.00 · Paid" under Invoices with a
   download link.
3. Auto top-up: the switch, the sentence with its two amounts and "Save" when they
   change; off, "Without it, Connexity pauses when your balance reaches $0."
4. Invoices: five, then "Show all".
5. With `SALES_CONTACT_URL` set: "Running a large fleet? Talk to us about volume
   pricing." opens that page; without it the line is absent.

### Code review

Four findings and one decision:

- **Fixed:** two scheduled runs that overlap could each charge the card for the same
  shortfall. Only one run can now take an agency's turn, and a claim left by a run that
  died is taken over after ten minutes.
- **Changed by Dmytro's decision:** auto top-up charged while most of the included
  $299 was unused, because it looked at the balance alone. It now charges only when
  both are used up (see Deviations).
- **Fixed:** every agency with auto top-up on cost a request to Stripe every minute.
  A turn with money left now asks Stripe nothing.
- **Fixed:** the new invoice calls had no test for a timeout, an empty answer and a
  malformed one.

The sandbox play-through above was run before the trigger changed. The new trigger,
the claim and the grace minute are covered by the tests with the invented Stripe
account, not by a second sandbox run.

### Not done

- **A top-up was not paid in a browser.** The Checkout page was made for real and
  checked at Stripe; the credit was proven with a real auto top-up invoice and Stripe's
  real event, not with a Checkout payment.
- **Automatic tax was not exercised,** for top-ups either: the sandbox refuses it until
  the head office address is in Stripe. With tax on, the balance gets the amount before
  tax; that is tested with the invented account only.
- **No email went through the real provider.** The three emails are tested up to the
  hand-over to SMTP, with their subjects and sentences checked.
- **The screens were not opened in a browser,** and the failed-payment line, the
  warning stripe and the expiring-card line cannot be produced on screen without a
  declined card in the sandbox.
- **Production:** `SALES_CONTACT_URL` (Dmytro's meeting page) and the extra Stripe
  message to register are Dmytro's settings; `docs-internal/billing.md` lists them.
