# Call ingestion

How calls reach Connexity. This is the written recommendation of roadmap feature 9
("Research: efficient call ingestion"), approved with the continuous call sync plan
(`plans/2026-11-12-continuous-call-sync.md`).

## Now: the webhook, set up by the assistant (Decided 2026-11-12)

"We dont need anything beyond retell webhook right now its part of setup" (Dmytro).

- **Retell sends every finished call** (`call_ended`, then `call_analyzed`) to
  `<backend>/api/v1/webhooks/retell/<connection id>`. The address is built from
  `OAUTH_ISSUER_URL`.
- **Connexity never writes to Retell,** so the assistant sets that address as each
  added agent's webhook, using its own Retell access. `add_agents` and `get_readiness`
  give the address.
- **The webhook is verified** with the connection's current key (Retell signs every
  request with it). It maps the call to a trace, resolves its versions, checks it, and
  stores it in every workspace that added that Retell agent from the same account. The
  second event for a call replaces the first.
- **Each agent records when its last call arrived by webhook.** Readiness step 3 and
  `get_readiness` name the added agents that have had none yet, so the person can tell
  "set up" from "not yet".

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
  webhook's.
- **Every step lists the next 25 calls** from the agent's position (including the
  position's own millisecond, so calls that started together are not skipped), skips
  those already stored, reads the rest in full 5 at a time, and stores them through the webhook's path.
  If a read fails, the position stops just before it and the step answers with an error;
  the next step asks for it again.
- **When an agent's window is done,** one pass resolves any versions still missing.
- **Readiness** counts "stored of total" from the database, so repeated or overlapping
  steps never miscount. The workspace records when the first scan first finished
  (`Company.first_scan_done_at`); step 4 stays done after that.

## Known gap, accepted (2026-11-12)

Retell retries a webhook a few times. A call that ends while the backend cannot answer,
for example during a deploy or an outage, is lost once the retries run out.

## Later, if needed: a safety-net pull

Not built, by decision. If missed calls start to matter, add a scheduled pull of every
added agent whose newest call is older than a few minutes. Cloud Run scales to zero, so
a loop inside the backend would stop; Cloud Scheduler calling a protected backend
endpoint wakes it instead. That costs nothing between runs, whereas keeping an instance
always on costs money every minute.

What bounds the load:

- each run asks only for calls newer than the newest stored;
- a few agents at a time;
- a time budget below Cloud Run's request limit;
- a database lock, so two runs never overlap.

Retell's call list carries no transcripts, so each new call is read once in full, by
whichever path brings it. That full read is the main cost either way.
