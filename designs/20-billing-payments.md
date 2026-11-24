# 20. Billing: paying

The Claude Design prompt for paying on Agency settings › Billing, from the roadmap rows
"Subscription and card" and "Top-ups, invoices and payment emails" (2026-11-23). The
result is `screens/Connexity Billing.dc.html` and the `billing` section of
`screens/Connexity Agency.dc.html`. How it works:
[`docs-internal/billing.md`](../docs-internal/billing.md).

Built so far: The model (the subscription only), Subscription, 3 Payment method and
4 Billing details. Sections 1, 2, 5, 6, 7 and 8 belong to "Top-ups, invoices and
payment emails"; the balance and usage above them belong to "Balance, included usage
and pause" and "Usage on the Billing page".

```txt
Add paying to Agency settings › Billing (Connexity Agency), in dark and light, in the empty space under the balance and usage. Keep the balance, usage and warnings as they are. Use the existing design system. Sentence case, plain words, no exclamation marks. Amounts in tabular figures. One primary button per screen. Orange is only the logo. Only Admins see any of this.

## The model
Each agency has one subscription: $299 a month, which includes $299 of usage. The included amount resets every month and does not roll over. Usage above it draws from a prepaid balance in dollars. There are no other plans and no seats. When the included amount and the balance are both used up, or the subscription is unpaid, Connexity pauses: new calls are not checked and tests can't run. Auto top-up is the calm way to avoid that. Card details are only ever entered on the payment provider's own page, never in Connexity.

## Subscription
A compact card at the top of this content:
- Active: "Connexity · $299 a month", the muted line "Includes $299 of usage · Renews 1 Dec", and a quiet "Cancel subscription".
- Not started: "Start your subscription", the line "$299 a month, includes $299 of usage", and the primary button "Start subscription", which opens the payment provider's page. While this button is showing, "Add funds" is hidden.
- Cancelled: "Active until 1 Dec", with "Resume subscription".
- Cancel dialog: "Cancel your subscription?" and "Connexity keeps working until 1 Dec, then pauses. Your balance of $412.50 stays on your account if you come back." Buttons: "Cancel subscription" (critical) and "Keep subscription".

## 1. Add funds
Next to the Balance at the top, the primary button "Add funds". It opens a small dialog on surface-2:
- Title: "Add funds"
- Three amounts as selectable tiles: $100, $500, $2,000, with $500 selected, and a fourth "Other amount" field (minimum $50).
- One muted line for the selected amount: "About 5 weeks at your current rate". Absent when there is not enough usage to tell.
- A line: "Plus tax where it applies. Added funds never expire and are non-refundable."
- Primary button: "Continue to payment", which opens the payment provider's page.
- Secondary: "Cancel".

After returning:
- Paid: a quiet confirmation line at the top of Billing, "$500.00 added to your balance", and the balance updates.
- Cancelled: nothing changes, no error.
- Still processing: "Your payment is processing. The balance updates when it's done."

## 2. Auto top-up
A simple card directly under the usage summary, with a switch:
- Title: "Auto top-up"
- Line: "Keeps Connexity running by adding funds before your balance runs out."
- When on, one editable sentence with two small inline fields: "When the balance falls below $50, add $200."
- Off with no card: the switch opens the payment provider's page to add one.
- When off, one muted line: "Without it, Connexity pauses when your balance reaches $0."

## 3. Payment method
One row: "Visa ending 4242 · expires 08/28" with "Change", which opens the payment provider's page. Without a card: "No card on file" and "Add card". A card about to expire shows a warning line.

## 4. Billing details
A compact row with the company name, address and tax ID, and "Edit", which opens the payment provider's page. These appear on invoices.

## 5. Invoices
A compact table, newest first: Date · Description · Amount · Status · download icon.
- "1 Dec 2026 · Subscription · $299.00 · Paid"
- "19 Nov 2026 · Auto top-up · $200.00 · Paid"
- "2 Nov 2026 · Added funds · $500.00 · Paid"
- Status can be Paid, Processing or Failed.
- Show 5, then "Show all".
- Empty state: "No invoices yet."

## 6. When a payment fails
- On Billing, one line in the critical colour above the balance: "Your auto top-up of $200 failed: the card was declined." with "Update card".
- A thin stripe at the top of the app, in the style of the existing stripes: "A payment failed. Update your card before your balance runs out." with the link "Update card". While the balance is still above zero, this stripe uses the warning colour.
- Once the balance reaches $0, the existing paused stripe replaces it.

## 7. Emails
Three short plain emails with the logo and one button each:
- "Your Connexity balance is low": the balance, about how long it will last, button "Add funds".
- "A Connexity payment failed": the amount, the reason, button "Update card".
- "Connexity is paused": "New calls are not being checked and tests can't run. Everything you have stays safe. Add funds and it resumes by itself." Button "Add funds".

## 8. Large volumes
One muted line at the bottom of Billing: "Running a large fleet? Talk to us about volume pricing."

## Show
- The whole Billing page, dark, desktop, with auto top-up on, a card and invoices.
- The Add funds dialog.
- A new agency after its first scan: no card, no invoices, auto top-up off, "Start subscription" as the clear next step.
- The cancel dialog.
- A failed payment, with the warning stripe.
- The three emails.
- The whole page in light, and at phone width with the invoices folded to Date, Amount and download.

## Avoid
- Card fields inside Connexity.
- More than one plan, tiers, seats, "Upgrade", or a free allowance.
- Credits or any unit other than dollars.
- Discounts or promo-code fields.
- Real names or card details: use invented values.
```
