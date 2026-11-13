# Scheduled call pull: the main way new calls arrive

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Scheduled call pull (main sync path)". It
  changes feature 8, "Continuous call sync".
- **Design:** No UI change.
- **MCP:** no new tool; the pull runs on its own. `add_agents` and `get_readiness` stop
  asking the assistant to set the webhook, and the guides change with them.

## Goal

Every added agent's new calls reach Connexity within about a minute, without anyone
setting anything in Retell. Retell allows one webhook per agent, and customers already
use it for their own automation (n8n), so the webhook cannot be the main path. Calls
come from a scheduled pull instead, and the webhook is used only where an agent's
webhook is free.

This replaces "nothing beyond the Retell webhook" (2026-11-12): "option A, go, Demo
milestone" (Dmytro, 2026-11-13, roadmap entry).

## What exists today

- **The webhook** (feature 8) stores a call seconds after it ends, in every workspace
  that added that agent from the same Retell account. It stays as it is.
- **The first scan** (feature 10) pulls an agent's last 30 days once, in steps, with its
  own position per agent. The pull reuses its pieces: listing without transcripts,
  reading calls in full, and storing through the webhook's path.
- **Readiness and `add_agents`** tell the assistant to set the webhook in Retell and
  name agents with no webhook call yet.
- **Retell's limits:** Retell's documentation gives no request rate for listing or
  reading calls, and no rate-limit headers. The list-calls page documents only a 429,
  "Account rate limited, please throttle your requests." Retell's real limit is 30 requests per 10 seconds
  per organization and route (question 2). The documented limits are
  on concurrent calls, not API requests.
- **Cloud Run** gives CPU only while a request is being answered, so work cannot run in
  the background between requests.

## Changes

### The pull (backend)

- **`POST /api/v1/internal/calls/pull`**, called by Cloud Scheduler every minute.
  - **Only Cloud Scheduler can call it.** The request carries a Google-signed identity
    token. The backend checks its signature against Google's public keys, its audience
    (this address) and its sender (the scheduler's service account, a new setting).
  - **Without those settings the route answers 404,** so local and test setups do
    nothing unless asked.
  - **The answer** is a short summary of the run: accounts pulled, calls stored, calls
    read again, accounts skipped and why. It has no call content.
- **One run at a time.** A run takes a lease in the database (a row with "held until",
  taken with one update) and gives it back at the end. A run that finds the lease held
  answers at once with "already running". A lease left by a crashed run ends after
  2 minutes. A lease row is used instead of an advisory lock because the database is
  reached through Supabase's pooler.
- **A run works per Retell account,** meaning per distinct API key. Workspaces connected
  with the same key share one pull, and each call is stored in every workspace that
  added that agent, as the webhook does.
  - **To group connections by key without decrypting every key on every run,** each
    connection stores a fingerprint of its key (a keyed hash, never the key). This also
    removes the webhook's decrypt-everything lookup, which feature 8's review flagged.
- **For each account, in a run:**
  1. **One list request,** for that account's added agents' calls that started after the
     account's position. The request asks for up to 1,000, oldest first, without
     transcripts. List requests are never sent in parallel for one account.
  2. **Calls already stored are skipped** (by the webhook, the first scan or an earlier
     run). Each new call that has ended is read in full, one at a time. It is then
     mapped, its versions resolved, checks run, and stored, the same way as the webhook.
  3. **The position moves past what was dealt with,** stopping just before the first call
     still in progress, so that call is listed again next run. A call still "in
     progress" two hours after it started is passed over; Retell's longest call is
     2 hours.
- **The first position of a new account** is the moment of its first run. Earlier calls
  are the first scan's: its window ends when the scan starts, and any overlap is
  stored once.
- **Late analysis:** Retell adds its post-call analysis a little after the call ends. A
  call stored without it is read once more, at least 2 minutes after it ended and within
  a day, and stored again (a replace). Each call is re-read once at most (a new
  `reread_at` on the call).
- **Idle accounts:** an account with no call in the last hour is pulled every 10 minutes
  instead of every minute.
- **Limits per run:**
  - at most 50 full reads per run across all accounts, oldest-pulled account first, so a
    backlog drains over several runs;
  - a time budget of 45 seconds, with Cloud Scheduler's deadline at 60.
- **On 429 or another failure from Retell:**
  - that account stops for this run, with its position kept;
  - it waits before its next pull: until `Retry-After` or `RateLimit-Reset` if Retell
    sends one, otherwise 1 minute, doubling to at most 10, with jitter;
  - the run carries on with the other accounts. There are no quick retries.
- **Each run logs one line** (accounts, calls, reads, skips, duration) like `call_sync`'s,
  with no call content.

### Webhook, Readiness and MCP

- **The webhook stays** and stays idempotent with the pull: whichever arrives first
  stores the call, and the other replaces it.
- **Setting the webhook leaves Readiness and onboarding:**
  - `add_agents` no longer gives the webhook step;
  - `get_readiness` no longer names agents with no webhook call;
  - the Connect guide says calls arrive within about a minute on their own, and that the
    webhook is optional, worth setting only if the agent's webhook is unused.
- **`docs-internal/call-ingestion.md`** is rewritten: the pull is the main path, the
  webhook is optional, the first scan covers history, and the decisions and limits
  above.
- **`docs-internal/deployment.md`:**
  - the backend's address is now `https://api.connexity.ai`;
  - the Cloud Scheduler job and its service account;
  - the two new settings;
  - the "keep an instance running" note is removed, because the work runs inside the
    scheduler's requests.

### Infrastructure (Dmytro's approval before anything is created)

In project `connexity-490409`, region `europe-west1`, after the pull request merges and
the backend has deployed:

1. A service account, `connexity-call-pull`, with no roles.
2. A Cloud Scheduler job, `connexity-call-pull`:
   - every minute;
   - `POST https://api.connexity.ai/api/v1/internal/calls/pull`;
   - an OIDC token for that service account, with that address as audience;
   - a 60-second deadline and no retries.
3. Two backend settings: `CALL_PULL_AUDIENCE` (that address) and `CALL_PULL_INVOKER`
   (the service account's email).

I write the exact `gcloud` commands into `deployment.md`. I run them only after your
explicit yes.

**Cost:** Cloud Scheduler's first 3 jobs are free. The runs are 1,440 short requests a
day to a backend that is already running, so about $0 now and a few dollars a month at
100 agents.

## Decisions

Decided by Dmytro (roadmap entry, 2026-11-13):

- A scheduled pull, every minute through Cloud Scheduler, is the main path. The webhook
  is used only where it is free.
- One list per account per run, never parallel within an account. New calls are read
  in full, late analysis is read once more, idle agents are pulled every 10 minutes,
  runs are capped, 429 means wait and skip, and a lock keeps runs apart.
- Setting the webhook leaves Readiness and onboarding.

Proposed by Claude:

- Cloud Scheduler's Google-signed token protects the route, not a shared secret.
- A lease row, not an advisory lock, because of the database pooler.
- A key fingerprint on each connection, to group accounts and to drop the webhook's
  decrypt-everything lookup.
- Reads are sequential within an account, 50 per run, with a 45-second budget.
- A new account starts from its first run; history is the first scan's.
- A call still "in progress" after 2 hours is passed over.

## Answered questions

Dmytro (2026-11-13):

1. Delete `Agent.last_webhook_call_at` and Readiness's "no call by webhook yet" step:
   "yes".
2. Retell's request limits: "30 requests per 10 seconds per organization and route"
   comes "from real limits of retell". The pull stays well under it: at most one list
   and 50 sequential reads per account per minute.
3. 50 reads per run, every minute: "sure".

## Done when

- `make check` passes. Backend tests (Retell mocked with `respx`, time controlled)
  cover:
  - a run storing new calls for several accounts, and twins (one key, two workspaces);
  - skipping stored calls;
  - the position stopping before a call in progress, and passing a 2-hour-old one;
  - the 50-read cap draining over runs;
  - a re-read of a call without analysis, once only;
  - idle accounts every 10 minutes;
  - 429 with and without a reset header, and backoff;
  - another account carrying on after one fails;
  - the lease (a second run at once, a stale lease);
  - the route refusing a missing, wrongly signed, wrong-audience or wrong-sender token,
    and answering 404 when not configured;
  - `add_agents` and `get_readiness` without the webhook step.
- Played through on a running backend with Retell's answers invented: runs every
  minute, calls arriving, a 429 and its backoff, a re-read.
- **After merge, with your approval:** the scheduler job created. On production, its
  runs succeed every minute (Cloud Run logs), and a test call to the production agent
  appears within about a minute with no webhook set.

## Out of scope

- Vapi and ElevenLabs.
- Showing sync health on screen.
- Changing the first scan.
- A relay or proxy for customers' own webhooks (rejected on 2026-11-13).

## Risks

- **Retell's limit is 30 requests per 10 seconds per organization and route** (question
  2). A run makes at most one list and 50 reads per account, so it stays under it; a
  429 pauses only that account.
- **Minute-by-minute requests keep the backend warm,** which is wanted, but every run
  costs one database round trip even when nothing changed.
- **A call that ends while its account is paused** arrives a few minutes late, not lost.
- **The key fingerprint uses a server-side secret.** If that secret changes, the
  fingerprints must be recomputed. A startup step fills in any that are missing.

## Outcome

### Deviations from the plan

- **Finished calls after a call still in progress are stored at once.** The position
  still waits just before the live call, so it is listed again, and calls already stored
  are skipped when listed again. In the plan, the run stopped at the live call, which
  would have held every later call back until it ended (from `/code-review`).
- **A call Retell keeps failing to return is passed over** after 3 failed runs in a row,
  so one call cannot stop an account's pull for good (from `/code-review`).
- **An unexpected error in one account** (for example Retell answering with something
  that is not JSON) is logged with its traceback and pauses that account; the run
  carries on. The play-through found that it failed the whole run. `backend/CLAUDE.md`
  asks for specific exception types; this follows the background call sync's existing
  boundary.
- **A call read well after it ended is not read again** for its analysis. If Retell has
  not added the analysis 2 minutes after the end, nothing more is coming.
- **The key fingerprint is keyed by the existing encryption key,** not a new secret.
- **The webhook address stays in `add_agents`** as an optional step, only for an agent
  whose webhook in Retell is empty, never replacing one. Readiness no longer mentions
  it.
- **Retell's 429** now raises `RetellRateLimited`, which carries `Retry-After` or
  `RateLimit-Reset`, for both the list and the read.

### Check results

`make check` on the final tree: see the table below.

| Step | Result |
|---|---|
| Plan present and complete | ok |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

New tests:

- `test_call_pull.py` (20, Retell answers invented with `respx`):
  - a run storing new calls per account and in every workspace that shares a key, with
    one list per account;
  - a new account starting from its first run;
  - stored calls not read again;
  - a call in progress holding the position but not later calls, and a 2-hour-old one
    passed over;
  - the read cap draining a backlog over runs;
  - a call without analysis read once more, once;
  - idle accounts every 10 minutes;
  - a 429 with and without `Retry-After`, pausing only that account;
  - an unexpected failure pausing only that account;
  - a call Retell keeps failing on passed over;
  - runs never overlapping, and a stale lease;
  - the route answering 404 when not set up, and 401 for no token, a garbage token, a
    wrong signature, audience, sender or issuer;
  - the scheduler's token running the pull.
- `test_retell_lists.py`: listing several agents at once, calls in progress flagged, and
  429 with `Retry-After`, `RateLimit-Reset` or neither, for the list and the read.
- `test_mcp_add_agents.py`: the webhook step only as optional, and Readiness with no
  webhook step.
- The webhook's "last webhook call" test is deleted with the column.

Migration `0016_scheduled_call_pull` applies on the local database with no drift.

**Played through on a running backend** (port 8022, local database). Retell's answers
were invented in the backend's process, and a local key stood in for Google's
signature. One account had 8 waiting calls, the read cap was 5, and older throwaway
accounts from earlier play-throughs were also in the database.

| # | Step | Came back |
|---|---|---|
| 1 | No token | 401 |
| 2 | A token from the wrong sender | 401 |
| 3 | A run | 200: 5 stored (the cap), the rest of the run skipped as full |
| 4 | A run | 200: the other 3 stored |
| 5 | A run | 200: nothing new; older accounts' calls read again once, for analysis |
| 6 | Retell answering 429 (`Retry-After: 90`) on one account; a new call on another | 200: that account paused (`rate_limited`), the other stored its new call |
| 7 | A run | 200: the paused account skipped (`paused`) |
| 8 | Retell adds the analysis to the new call, which is now over 2 minutes old | 200: 1 call read again |
| 9 | A run | 200: nothing read twice |

The route is not in the OpenAPI schema. The backend log had a `call_pull` line per run
and no errors. A first attempt answered 500 from run 2 onward: my mock crashed on call
ids it did not know, and the run had no boundary for an unexpected error. Both were
fixed, and the run was replayed as above.

`/code-review` (high) raised five findings. Fixed: a call Retell keeps failing on
stopped its account for good; a live call delayed every later call; an unexpected error
failed the whole run. Not fixed:

- **The broad exception boundary** goes against "Catch specific exception types", for
  the reason above.
- **Google's public keys are fetched with a blocking request** on first use and when
  they rotate, inside an async route. It is one short fetch on a cold instance.

**After merge, with Dmytro's approval:**

1. Create the service account and the Cloud Scheduler job, and set the two backend
   settings (the commands are in `docs-internal/deployment.md`).
2. In the backend's logs, check a `call_pull` line every minute.
3. Make a test call to the production agent, with no webhook set. It appears in
   Readiness's count within about a minute.

### Not done

- **The Cloud Scheduler job and service account** are not created yet; they need your
  approval after merge.
- **Not run against the real Retell API.**
- **Throwaway data in the local dev database:** two play-through users, their test
  Retell connections, agents and invented calls.
