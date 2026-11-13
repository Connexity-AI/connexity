# Call ingestion

How calls reach Connexity: the scheduled pull for new calls, the first scan for history,
and an optional webhook. The pull replaces "nothing beyond the Retell webhook"
(2026-11-12): "option A, go, Demo milestone" (Dmytro, 2026-11-13). Plan:
`plans/2026-11-13-scheduled-call-pull.md`.

## Why a pull

Retell allows one webhook per agent, and customers already use it for their own
automation (n8n). So Connexity cannot rely on it: a scheduled pull is the main path, and
the webhook is used only where an agent's webhook is free. A relay that forwards a
customer's webhook was rejected.

## Now: the scheduled pull (Decided 2026-11-13)

Cloud Scheduler calls `POST /api/v1/internal/calls/pull` every minute
(`app/services/call_pull.py`, route in `app/api/routes/internal.py`).

- **Only Cloud Scheduler can call it.** It sends a Google-signed identity token. The
  backend checks the signature against Google's keys, the audience
  (`CALL_PULL_AUDIENCE`, the route's address) and the sender (`CALL_PULL_INVOKER`, the
  scheduler's service account). Without both settings the route answers 404, so local
  setups never pull.
- **The work runs inside that request.** Cloud Run gives CPU only while it answers, and
  the minute requests are what keep the pull going.
- **One run at a time:** a lease row (`call_pull_lease`), taken with one update, held
  for at most 2 minutes. It is not an advisory lock, because the database is reached
  through Supabase's pooler, which does not keep a session's state.
- **Per Retell account,** meaning per API key. Each connection stores a keyed hash of
  its key (`Integration.key_fingerprint`), so connections holding the same account are
  found without decrypting every key. The webhook uses the same lookup. Each account
  keeps its position, pause and failure count in `call_pull_account`.
- **Each run, per account,** oldest pulled first:
  1. **One list request** for the account's added agents' calls since its position (up
     to 1,000, oldest first, no transcripts). Lists are never sent in parallel within an
     account.
  2. **Calls already stored are skipped.** Each new call that has ended is read in full
     (one at a time) and stored, through the webhook's path, in every workspace that
     added its agent.
  3. **The position moves past what was dealt with,** stopping just before a call still
     in progress, so that call is listed again next run. A call "in progress" for more
     than 2 hours is passed over.
- **A new account starts from its first run.** Its history is the first scan's.
- **Late analysis:** a call stored without Retell's post-call analysis is read once
  more, 2 minutes to a day after it ended (`Call.reread_at`).
- **Idle accounts** (no call in the last hour) are pulled every 10 minutes.
- **Limits per run:** 50 full reads across all accounts, and 45 seconds (Cloud
  Scheduler's deadline is 60). A backlog drains over several runs.
- **Retell's limit:** 30 requests per 10 seconds per organization and route (Dmytro,
  2026-11-13; not in Retell's public documentation). A run sends one list and at most 50
  sequential reads per account, which stays under it.
- **On a 429 or another failure,** that account stops for this run with its position
  kept. It waits `Retry-After` or `RateLimit-Reset` if Retell sends one, otherwise
  1 minute doubling to 10, plus jitter. The other accounts carry on, with no quick
  retries.
- **Each run logs one `call_pull` line:** accounts, calls stored and re-read, reads,
  skips and duration, never call content.

## Optional: the webhook

`POST /api/v1/webhooks/retell/<connection id>`, verified with the connection's key.
It stores a call seconds after it ends, in every workspace that added that agent from
the same account. The assistant sets it only where an added agent's webhook in Retell is
empty, never replacing one; `add_agents` gives the address. It is not part of Readiness
or onboarding. Whichever of the pull and the webhook arrives first stores the call, and
the other replaces it.

## History: the first scan

The last 30 days of each added agent's calls are pulled once by the first scan
(`app/services/first_scan.py`, plan `plans/2026-11-12-first-scan.md`). The assistant
drives it through MCP, calling `scan_calls` until it says finished:

- **Each step works for up to about 40 seconds** and stops; nothing runs after the answer,
  because Cloud Run slows work once a request has been answered. The MCP server waits up
  to 180 seconds for a step: a page that started before the 40 seconds ran out is
  finished, and counting a large window takes a step of its own.
- **Each agent keeps its own position** (`Agent.scan_cursor`), separate from its newest
  stored call. The 1.x pull (`sync_agent_calls`) starts after the newest stored call, so
  one webhook call would hide the whole history from it.
- **The first step for an agent lists the window** from Retell (no transcripts, 1,000
  per page) to know the total, and fixes its end at that moment. Later calls are the
  pull's.
- **Every step lists the next 25 calls** from the agent's position (including the
  position's own millisecond, so calls that started together are not skipped), skips
  those already stored, reads the rest in full 5 at a time, and stores them through the webhook's path.
  If a read fails, the position stops just before it and the step answers with an error;
  the next step asks for it again.
- **When an agent's window is done,** one pass resolves any versions still missing.
- **Readiness** counts "stored of total" from the database, so repeated or overlapping
  steps never miscount. The workspace records when the first scan first finished
  (`Company.first_scan_done_at`); step 4 stays done after that.

## Known gaps

- **A call that ends while its account is paused** after a 429 or a failure arrives a
  few minutes late, not lost.
- **The fingerprint is keyed by the encryption key.** If that key changes, stored keys
  become unreadable anyway, and connections must be made again.
