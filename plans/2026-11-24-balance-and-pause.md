# Balance, included usage and pause

- **Owner:** Dmytro
- **Slice:** Balance, included usage and pause (roadmap Order 102.4), one pull request
  (Decided by Dmytro, 2026-11-24). Built after "Subscription and card", whose state it
  reads.
- **Design:** the prompt in the roadmap row (2026-11-23), sections 1, 5 and 6. The
  export of 2026-11-24 holds the sidebar's "Balance low" line (`Connexity Sidebar`,
  already in the repo) and the three stripes (`Connexity Readiness Bar`, copied in with
  this change). The balance figures on Agency settings › Billing are the row "Usage on
  the Billing page".
- **MCP:** `get_usage` also answers the included amount, what is left of it, the balance
  and the state; `run_scenarios`, `scan_calls` and `add_agents` are refused while paused,
  with what to tell the person. Contract entries updated.
- **Status:** Approved by Dmytro ("Accept, build", 2026-11-24).

## Goal

Connexity knows what every agency has left (this period's included $299, then a prepaid
balance in dollars) and acts on it: when both are used up, or there is no paid
subscription, new calls are not recorded or checked and tests cannot run, until money
arrives. A new agency gets its first scan without paying. People see it in a stripe at
the top of the app and a line in the sidebar; an assistant is told the same.

## What the code is today

- **Usage is counted per workspace, at list price, and never charged** (`usage_record`,
  `app/services/usage.py`).
- **The subscription's state is known** per agency (pull request 265), and nothing reads
  it.
- **Calls arrive in three places** (the Retell webhook, the scheduled pull with the
  first scan, and the trace ingest route) and **tests start in one**
  (`services/test_run.py`). A pause acts there.
- **The app has no stripe yet;** the design's stripes are new to the build.

## Changes

### The money

- **Included amount:** $299 for each period of a subscription that is active or past
  due. It does not roll over. The period is the subscription's, not the calendar month.
- **Balance:** a ledger per agency (`balance_entry`: amount, kind, note, who, when).
  The balance is what was added minus what usage drew. In this row the only way to add
  is an entry made by Connexity; top-ups come with their own row.
- **Drawing down:** the period's usage at list price comes off the included amount
  first, then the balance. The balance never goes below zero: the call that crosses the
  line is recorded and checked, and what it costs beyond the money left is not charged.
- **First scan included:** an agency with no subscription gets its first scan and
  dashboard, up to the limit: the last 30 days, the latest 100 calls per agent, at most
  500 calls per agency, one included scan per voice platform account. When the limit
  cut the scan short, the first-scan stripe says so. That usage is marked and never drawn from
  anything.

### The states

Worked out from the above in one place, per agency:

| State | When | What happens |
|---|---|---|
| `first_scan` | No subscription, first scan not finished | Scan runs up to the limit |
| `needs_subscription` | No subscription (never started, or ended), first scan done | Paused; calm stripe "Your first scan is done. Start your subscription to keep checking new calls and run tests." with "Start subscription" |
| `active` | Subscription active or past due, money left | Everything runs |
| `low` | As `active`, and less than about a week left at the rate of the last 7 days | Sidebar line "Balance low · 3 days left", linking to Billing |
| `out` | Subscription active or past due, included amount and balance both used up | Paused; critical stripe "You've used this month's usage. Connexity is paused: new calls are not being checked and tests can't run." with "It resumes when your next period starts on 1 Dec." and no "Add funds" link until top-ups exist |
| `unpaid` | Subscription unpaid | Paused; stripe "Your subscription is unpaid. Connexity is paused." with "Update card" |

- **Only where paying is set up.** On a deployment without Stripe settings (self-hosted,
  and production until the live keys are in) nothing is drawn, nothing pauses and no
  stripe shows.
- **Resuming needs no step:** a payment, a new period or an added balance changes the
  state the next time it is worked out.

### The pause

- **Not recorded, not checked:** the webhook, the scheduled pull, the first scan beyond
  its limit and the trace ingest route store nothing for a paused agency's workspaces.
  The webhook still answers the voice platform with success, so it does not retry.
- **Never caught up** (Decided): the pull's position moves on during a pause, so calls
  made then are not brought in later. Each pause is recorded with its start, end and
  reason.
- **Tests cannot start:** `start_run` refuses, on the web and for an assistant.
- **Everything already recorded stays readable.**

### Screens (as designed)

- **The stripe** at the top of the app, in the three wordings above. "Start
  subscription" and "Update card" open Agency settings › Billing.
- **The sidebar line** "Balance low · 3 days left".

### Assistants

- **`get_usage`:** `included` (amount, used, left, when the period ends), `balance`,
  `state`, and about how many days it lasts when that can be told.
- **Refusals while paused:** `run_scenarios`, `scan_calls` and `add_agents` answer what
  is paused, why, and that an Admin resumes it in Agency settings › Billing. Reading
  tools keep working.

### Docs

- `docs-internal/billing.md` (money, states, pause), `usage.md`, `data-model.md`,
  `decisions.md`, `mcp-architecture.md`, `designs/README.md`.

## Decisions

- **Decided (Dmytro, 2026-11-23, roadmap row):** $299 a month includes $299 of usage,
  then one prepaid balance in dollars per agency; no credit unit; pause everything when
  both are used up or the subscription is unpaid; the balance never goes negative;
  everything recorded stays readable; resuming is automatic; the first scan is included
  with a cost limit.
- **Decided (Dmytro, 2026-11-24):** calls made during a pause are never brought in
  afterwards; one pull request; "Subscription and card" first; a failed renewal still
  being retried (`past_due`) keeps Connexity working.
- **Proposed:** nothing pauses on a deployment where paying is not set up.
- **Proposed:** "low" means less than 7 days left at the average of the last 7 days;
  with less than 3 days of usage to go on, never low.
- **Proposed:** pauses are recorded now; showing the paused days on the Dashboard needs
  a design and is not in this row.
- **Decided (Dmytro, 2026-11-24):** the first scan covers the last 30 days, the latest
  100 calls per agent, at most 500 calls per agency, and one included scan per voice
  platform account. His reason: there are few checks today and there will be many more,
  so Connexity's cost per call will grow.
- **Decided (Dmytro, 2026-11-24):** until top-ups exist, the paused stripe for "out"
  shows without "Add funds", with the date the next period starts. Connexity can add
  balance by hand.
- **Decided (Dmytro, 2026-11-24):** an agency that already exists when paying is
  switched on gets no grace period: it is paused until an Admin starts the
  subscription, like a new agency whose first scan is done.

## Done when

- Through the API on the local database, with the subscription state set directly:
  below $299 the included amount goes down and the balance is untouched; above it the
  balance goes down and stops at zero; a new period restores the included amount and
  keeps the balance; first-scan usage draws from nothing and stops at the limit; each
  state in the table is reached and left again by the event that should end it.
- While paused: a webhook call, a pulled call and an ingested trace are not stored; a
  test run is refused on the web and for an assistant; calls made during the pause are
  not brought in after it; reading still works.
- Without Stripe settings nothing pauses.
- MCP server tests pass with the changed tools and contract entries.
- Frontend types and lint pass; the full `make check` passes.

## Out of scope

- Adding funds, auto top-up, invoices, the failed-payment stripe and the three emails
  (row "Top-ups, invoices and payment emails").
- The balance and usage figures on Agency settings › Billing, and the CSV (row "Usage
  on the Billing page").
- Showing paused days on the Dashboard.
- Voice simulation minutes: they do not exist yet.

## Risks

- **A wrong state pauses a paying agency.** The state is one pure function with a test
  per row of the table, and a pause never deletes anything: the worst case is calls not
  recorded until it is corrected.
- **Calls not recorded during a pause are gone for good,** by decision. The stripe says
  that new calls are not being checked.
- **Until top-ups exist, an agency that uses more than $299 in a period can only wait
  for the next period,** unless Connexity adds balance by hand.
- **A paused agency's stored calls are still re-checked** when a check changes. That is
  Connexity's cost, bounded by what the agency already had; stopping it is a small
  follow-up.

## Outcome

### Deviations from the plan

- **Usage is charged in the period Connexity recorded it,** not marked as "first scan".
  The first scan is recorded before there is a subscription, so it falls in no period
  and is never charged; a later scan of older calls is recorded now and is charged.
  The usage page counts by when a call happened, so the two can differ at a period's
  edges.
- **During the first scan only the scan stores calls.** A call arriving by webhook or
  the pull while an agency has no subscription is not recorded, also before the scan
  has finished. Otherwise the limit could be passed by simply receiving calls.
- **A new route, `GET /agencies/{id}/billing/status`,** for the stripe and the sidebar
  line. Anyone in the agency may read it.
- **The stripe has two wordings that are not in the design:**
  - when a subscription existed and ended: "Your subscription has ended. Connexity is
    paused: new calls are not being checked and tests can't run." with "Start
    subscription"; the designed sentence starts "Your first scan is done.", which would
    be wrong for them;
  - when the limit cut the first scan: "Your first scan checked the latest 500 of 3,410
    calls." in place of "Your first scan is done."
- **The trace ingest route answers 402** while paused, where the webhook answers
  success. A team sending its own traces should learn they were not stored; Retell
  would only retry.
- **A test run is refused before anything is asked of the voice platform,** in the
  assistant's route as well as in `start_run`.
- **A script adds balance by hand** (`backend/scripts/add_balance.py`): the plan said
  Connexity can, and nothing else could.
- **Tests no longer read a developer's Stripe settings:** a shared fixture clears them,
  so the suite runs the same with a sandbox key in `.env` as in CI.
- **This branch was built on "Subscription and card"** while pull request 265 was open;
  `main` was merged in after it merged, and the branch now differs from `main` by this
  change only.

### Check results

Route tests through the API on the local database (`TestClient`; no separate
play-through server), with paying switched on by invented settings and the
subscription's state set as Stripe's messages would set it:

| What | Result |
|---|---|
| `test_balance_and_pause.py` (15 tests): usage comes off the included amount, then the balance, which stops at zero, with one ledger line per period that settling twice does not change; a new period restores the included amount and keeps the balance, counting usage that arrived after the last settling; what was recorded before the subscription is never charged; every state is reached and left by the right event, and each pause is recorded and closed; low needs under a week left and usage on three days, and is not low when the next period comes first; a paused agency's webhook call is not stored and Retell is answered with success, scanning, adding agents and a test run are refused with what to tell the person, reading still works, and a subscription resumes it; the pull passes over a paused agency's calls and does not go back for them; an ingested trace is refused while paused and stored after; where paying is not set up nothing pauses; the included first scan reads the latest calls up to the limit per agent and per agency and reports how many the window held; a subscribed agency's scan has no limit; a second agency on the same voice platform account gets no included scan; an agency that only sends its own traces is asked to subscribe; two open pause records do not break an agency | passed |
| Billing, scan, pull, webhook, ingest, test-run, usage and schema tests | passed |
| MCP server tests (68), with `money` on `get_usage` | passed |
| Backend `ruff` and `pyright`; frontend types, lint and formatting; client regenerated | passed |
| Full `make check`, after the review fixes and with `main` merged in | passed, every step |

For Dmytro to check on screen, with the sandbox key in `.env` (against
`designs/screens/Connexity Readiness Bar.dc.html` and the sidebar):

1. A new account with agents added and scanned: the calm stripe "Your first scan is
   done. Start your subscription to keep checking new calls and run tests." with
   "Start subscription" opening Billing.
2. After starting the subscription in the sandbox: the stripe is gone.
3. Without the Stripe settings: no stripe anywhere, nothing paused.
4. The "out", "unpaid" and "Balance low" states need usage or a Stripe state that is
   slow to produce by hand; their wording is in `billing-stripe.tsx` and their logic is
   tested.

### Code review

Two findings, both fixed:

- Two requests working out one agency's state at the same moment could each open a
  pause record, after which every request for that agency failed. Open pauses are now
  read as a list and extras closed; a lost race on the period's ledger line or on the
  included-scan record is treated as already done. Tested.
- An agency that sends its own traces and has no voice platform agents stayed in
  "first scan" for ever: its traces were refused and no stripe told it why. It now
  needs a subscription like any other, and the stripe says so. Tested.

One thing found and left: when a call stops counting as usage and later counts again,
its usage row is made anew and is charged in the period it reappears in. It is rare (a
call re-stored with another source) and bounded to that one call.

### Not done

- **Not verified on screen:** the stripe and the sidebar line were not opened in a
  browser.
- **No real money moved:** the states were driven by setting the subscription directly,
  not by Stripe. The first real period, renewal and failed payment happen in production.
- **Showing paused days** on the Dashboard (needs a design).
- **Re-checks of calls already stored** still run for a paused agency when a check's
  version changes. They cost Connexity model money and are not charged. See Risks.
