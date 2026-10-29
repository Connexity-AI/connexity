# Retell's retired list endpoints

- **Owner:** Dmytro
- **Slice:** 1.3c (outside the roadmap's order; it blocks testing with real calls)

## Goal

Retell stopped serving its old list endpoints (announced for after 2026-06-15). Since
then every pull of calls fails: Refresh does nothing, the background sync logs "Retell
API returned an error", and no call newer than 2026-10-09 has arrived on Dmytro's
machine although Retell holds more than 100 newer ones for one agent. Connecting a
Retell account fails too, because its connection test uses the old agent list.

After this merges, calls are pulled again, missing ones included, and a Retell account
can be connected and its agents listed.

## Changes

**Pulling calls**

- Calls are listed with Retell's new call list (`POST /v3/list-calls`): its filter
  format (agent, and start time after the newest stored call), oldest first.
- The new list no longer carries the transcript or the recording. Each new finished call
  is therefore read once in full (`GET /v2/get-call/{call_id}`), a few at a time, and
  that full record is what gets mapped and stored, exactly as before.
- If reading one call fails, the batch stops just before it, so the next pull starts
  from that call and nothing is skipped.

**Connecting an account and listing agents**

- The connection test and the agent list use Retell's new agent list
  (`POST /v2/list-agents`), reading every page.
- The new list has no "published" flag and no version per agent. "Published" becomes
  "has a latest published version", and the version shown is that latest published
  version.

**Not changed**

- Reading an agent, its prompt and one call: those endpoints still work.
- The webhook.
- The frozen eval stack, including its use of the retired agent version list.

## Decisions

Made by Dmytro on 2026-10-28: do this slice now ("do it"), on the scope described to
him: new call list plus a full read per new call, new agent list for the connection
test and the agent picker, frozen code left alone, proven by pulling the missing calls.

Proposed by Claude, not separately confirmed:

- Up to 5 calls are read in full at the same time.
- A failed full read ends the batch there rather than skipping the call.

## Done when

- With invented Retell responses: a pull asks the new call list with the agent and the
  start time, reads each finished call in full, maps and stores it; an unfinished call
  is not read; a failed full read stops the batch before that call and the next pull
  asks again from there.
- Retell being unreachable, slow, or answering an error or something malformed during a
  pull gives the same error to the person as before and stores nothing wrong.
- The connection test passes with a working key and fails with a refused one; the agent
  list reads every page and marks published agents.
- **On Dmytro's machine:** Refresh on the agent whose calls stopped on 2026-10-09 brings
  the missing calls in. Reported as counts.
- `make check` passes.

## Out of scope

- Vapi and ElevenLabs.
- The frozen eval stack's calls to Retell.
- Reading pages of the call list by Retell's own cursor; the start time of the newest
  stored call keeps serving as the cursor.

## Risks

- **A pull now costs one request per new call** on top of the list. A first pull after a
  long gap reads hundreds of calls one by one, a few at a time.
- **Other retired endpoints may surface later.** Only those Connexity's live code calls
  were checked.
- **The webhook still works and would have kept calls arriving.** It is not set up for
  Dmytro's agents; nothing here changes that.

## Outcome

### Deviations from the plan

- **A pull stops at a call still in progress** (Retell status registered or ongoing)
  instead of skipping it. Skipping it while returning later calls would have moved the
  next pull past it for good. A call that never connected is still skipped. Found in
  review.
- **A pull where no call at all can be read in full is an error**, not an empty result,
  so a broken full read cannot look like "no new calls". Found in review.
- **For Retell, a short page no longer ends a pull.** The new list drops unfinished calls
  and stops at a failed read, so a page often returns fewer than 100. The pull reads on
  until a page brings nothing new. One existing test now expects two list requests in
  one sync instead of one; the test's point, one sync per staleness window, is
  unchanged. Found in review.
- **The inbound agent was stuck too**, and got its missing calls in the same run.

### Check results

`make check` on this branch:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 9s |
| Backend tests and coverage | ok | 72s |
| MCP server tests | ok | 2s |
| Frontend lint | ok | 1s |
| Frontend types | ok | 2s |
| Generated client is fresh | ok | 9s |

The plan step failed in the full run because this Outcome was not yet written. It was
re-run on its own afterwards and passed; nothing else changed in between.

Against the done-when (new tests in `test_retell_lists.py`, invented responses):

| Done when | Result |
|---|---|
| A pull asks the new list with agent and start time, reads each finished call in full, stores it; an unfinished call is not read; a failed read stops the batch before it | Yes. Also: a call never connected is skipped, a call in progress stops the pull, a call Retell no longer has is skipped |
| Unreachable, slow, error or malformed during a pull gives the same error as before | Yes, for the list (timeout, 400, 500, empty, not JSON, wrong shape) and for the full read (timeout, not JSON, 429) |
| Connection test passes with a working key, fails with a refused one; the agent list reads every page and marks published agents | Yes |
| On Dmytro's machine, the missing calls come in | Yes, see below |
| `make check` passes | Yes, with the note above |

Real calls, on Dmytro's machine, counts only, through the same pull the Refresh button
runs:

| Agent | Before | After | Newest call |
|---|---|---|---|
| The booking agent whose calls stopped on 2026-10-09 | 597 | 647 | 2026-10-28 |
| The inbound agent | 216 | 296 | 2026-10-28 |

"Before" is the count when the calls stopped. The booking agent's missing calls came in
over three pulls: the running local server once it reloaded with the new code, then two
runs of the same pull from the session, the first before the review fixes. A further
pull right after brought nothing new on either agent. Every stored call has a trace.
With the connected key, the connection test passes and the agent list returns 19
agents.

Before the change, Retell answered both old endpoints with "Deprecated API usage is no
longer supported", and the background sync had logged "Retell API returned an error" on
every attempt.

**`/code-review`** was run on the diff before the fixes. Six findings, five fixed:

| Finding | Outcome |
|---|---|
| A pull where every full read fails looked like "no new calls" | Fixed |
| A call in progress was skipped and then passed for good | Fixed |
| A short page ended the pull although more calls were waiting | Fixed |
| No backoff when Retell rate-limits the full reads | **Not fixed.** See below |
| No timeout or malformed-answer test for the full read | Fixed |
| An unused parameter in a test helper | Fixed |

The review was done by the session that wrote the code, not an independent reviewer.

### Not done

- **No backoff on rate limits.** If Retell throttles the full reads, a pull stops at the
  throttled call and the next pull carries on from there. Nothing is lost, but a large
  backlog drains in pieces.
- **The frozen eval stack still calls the retired agent version list.** Nothing live
  uses it.
- **The screens were not looked at.** Nothing on screen changed; the Calls list simply
  fills again.
- **The webhook is still not set up** for Dmytro's agents. It would have kept calls
  arriving through this outage.
