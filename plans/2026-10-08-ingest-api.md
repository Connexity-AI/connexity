# Ingest API: accept a trace from outside, with its own tokens

- **Owner:** Dmytro
- **Slice:** 1.2

## Goal

Let something outside Connexity send it a call. Slice 1.1 made it possible to store a
trace; nothing can deliver one yet, because the only ways to authenticate are a browser
cookie and the assistant's OAuth login, and a webhook or a script has neither. After
this merges, a caller holding an ingest token can post a trace for any agent of its
company, and gets back what Connexity made of it.

## Changes

**Ingest tokens**

- A new kind of credential: an ingest token, bound to one company. It can do exactly
  one thing: send traces for that company's agents. It cannot read anything.
- A token is shown once, when it is created. Connexity stores only a hash of it, plus
  its name, a short visible prefix (so a token can be recognised in a list), when it
  was last used, and when it was revoked.
- A logged-in user can create, list and revoke their company's tokens through the API. There
  is no screen for it: tokens are set up through the assistant, and the assistant gets
  its tools for this in slice 1.8.

**The ingest endpoint**

- `POST /api/v1/ingest/traces`, authenticated with `Authorization: Bearer <token>`.
- The body names the agent (its Connexity id), carries a trace in the published format,
  and optionally the provider's original payload, which is stored unmodified beside the
  call.
- The company is taken from the token, never from the body. An agent of another company
  is treated as not found.
- Sending the same call again (same `external_id` for that agent) replaces what was
  stored. That is how a corrected mapping re-sends past calls.
- The response says: the call's id, whether it was created or replaced, the trace's
  capabilities, and which capabilities are missing.
- Rejections, each with a clear message: no token or an unknown or revoked token (401);
  a trace that does not match the schema (422, naming the field); a body over the size
  limit (413).

**Limits**

- A request body may be at most 5 MB, and a trace at most 5,000 events. Both are
  settings.

**Fix carried from slice 1.1**

- Two simultaneous sends of the same new call no longer fail. One creates the call and
  the other replaces it.

## Decisions

Made by Dmytro on 2026-10-08:

- **A token belongs to the company, not to one agent**, to keep setup simple. The
  sender names the agent in each request. This can be narrowed later.
- **The endpoint accepts traces only, not provider payloads.** Converting a provider's
  own payload is a mapping's job. Retell's mapping, and the address Retell's webhook
  posts to, are slice 1.3. This endpoint is what a self-hosted agent, a script, or a
  mapping run elsewhere uses.
- **A token never expires on its own.** It is valid until revoked.
- **Resending replaces; it does not merge.** The latest trace for a call wins whole.
- **No screen for tokens.** They are created through the API now and through the
  assistant once its tools exist (slice 1.8).
- **No rate limiting in this slice.** Only the size limits above.

Proposed by Claude, not separately confirmed:

- `source` is taken from the trace as sent. A token is not restricted to production or
  test calls.

## Done when

- With a valid token, posting each of the three published example traces returns
  success, the right capabilities, and "created"; posting one again returns "replaced"
  and the stored trace equals the second one sent.
- The stored call belongs to the token's company and the named agent.
- A token cannot write to an agent of another company; the response is the same as for
  an agent that does not exist.
- A missing, malformed, unknown or revoked token is refused with 401, and the response
  does not reveal which of those it was.
- An invalid trace is refused with 422 and the message names the offending field.
- An oversized body is refused with 413.
- A token's secret is returned only by the create call. Listing shows name, prefix,
  created, last used and revoked, never the secret, and the database holds no secret.
- Sending the same new call from two requests at once stores one call and neither
  request fails.
- A user cannot create, list or revoke tokens for another company's agent.
- `make check` passes.

## Out of scope

- A provider webhook address and any provider mapping (slice 1.3).
- Tools for the assistant to manage tokens or read calls (slice 1.8).
- A screen for tokens.
- Running checks on ingest (Phase 2). The response reports capabilities only.
- Rate limiting, and scoping a token to production or test calls.
- An OpenTelemetry endpoint.

## Risks

- **An ingest token is a write credential that lives in someone else's system** (a
  webhook configuration, a script's environment). It can only send traces and it is
  revocable, but anyone holding it can add false calls to any agent of the company, or
  overwrite a real call's trace by resending its `external_id`. Company-wide scope was
  chosen knowingly, for simplicity.
- **Replace-on-resend can destroy a good trace** if a bad mapping resends. The
  provider's original payload is kept only when the sender includes it.
- **No rate limit** means a looping sender can fill the database. Size limits bound a
  single request, not the number of requests.
- **A reviewer should push back if** replace-on-resend should instead keep history.

## Outcome

### Deviations from the plan

- **The size limit is weaker than the plan implied.** A body over 5 MB is refused with
  413, as planned. But the web framework has already read the whole body into memory
  by the time Connexity can check it, so the limit bounds what is accepted and stored,
  not what the server reads. Real protection against a sender streaming a huge body
  belongs in the proxy in front of the API. The code says so.
- **A caller with a bad token always gets 401, even with an oversized body.** Not in the
  plan; added so an unauthenticated caller learns nothing about limits.
- **`store_trace` now returns two things:** the call, and whether it was created. The
  three tests from slice 1.1 that call it were adjusted.
- A public guide, `docs/traces/ingest.md`, was added. The plan did not list it.

### Check results

`make check` on this branch:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 17s |
| Backend tests and coverage | ok | 87s |
| MCP server tests | ok | 4s |
| Frontend lint | ok | 10s |
| Frontend types | ok | 9s |
| Generated client is fresh | ok | 11s |

The plan step failed in the full run because this Outcome was not yet written. It was
re-run on its own afterwards and passed; nothing else changed in between.

Against the plan's done-when (21 new tests in `test_ingest.py`):

| Done when | Result |
|---|---|
| Each published example ingests, with the right capabilities, as "created" | Yes |
| Resending returns "replaced" and the stored trace is the second one | Yes |
| The stored call belongs to the token's company and the named agent | Yes |
| Another company's agent is refused, identically to a missing agent | Yes: both 404 with the same body, and nothing is stored |
| Missing, malformed, unknown or revoked token gives 401 without saying which | Yes; a login cookie is also refused |
| Invalid trace gives 422 naming the field | Yes |
| Oversized body gives 413 | Yes |
| The secret is returned only on create and is not in the database | Yes |
| Two simultaneous stores of a new call: one call, no failure | Yes: one reports created, the other replaced |
| Tokens cannot be listed or revoked across companies | Yes |

Migration `0003_ingest_token` applies, reverses and re-applies, and `alembic check`
reports no drift.

Review of the diff by the building session found the size-limit overstatement above
(a comment claimed the body was refused before being read); corrected. `/code-review`
was not run as a separate pass.

### Not done

- Not tried by hand with `curl` against a running server; only through the test client.
- No rate limiting, as planned.
- The 5 MB limit does not stop the server reading a larger body (see deviations).
- A request with malformed JSON and a bad token gets 422, not 401, because the
  framework parses the body before checking the token. It reveals nothing about tokens.
- Resending a call that was soft-deleted (its integration was removed) stores the trace
  but leaves the call hidden. Not handled; noted for slice 1.3.
