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

Calls from before the webhook was set are pulled once, on request, by the first scan
(roadmap feature 10), using the incremental pull (`sync_agent_calls`). That pull asks
Retell for an agent's calls after the newest stored one, 100 at a time.

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
