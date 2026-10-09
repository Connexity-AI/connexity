# Executions are found without a button

- **Owner:** Dmytro
- **Slice:** 1.4 (follow-up)

## Goal

Remove the **Find executions** button from the call drawer. A person should not have to
tell Connexity to look for something it already knows is missing. After this merges, a
tool call whose execution has not been looked for is looked up on its own, and the
button is gone.

## Changes

**When Connexity looks, without being asked**

- As today: when a call arrives, by pull or by webhook.
- New: **when a tool's mapping is saved or changed.** The recent calls that used that
  tool are looked up again, after the response.
- New: **in the background sync** that runs when an agent's calls are opened and the
  list is stale. Any recent call with a mapped tool call that has not been looked up yet
  is looked up, up to 50 calls per pass.

**Knowing what has been looked up**

- A call records when its executions were last looked for. A lookup that n8n answered
  cleanly counts, whether or not it found anything. A lookup that hit a problem (n8n
  down, an answer that made no sense) does not count, so it is tried again.
- After a pass with a problem, the next automatic pass for that agent waits ten minutes.

**How far back**

- Only calls from the last 30 days are looked up automatically. A backend keeps its
  history for a while only, and an older call will never find anything. The number is a
  setting.

**The screen and the API**

- The **Find executions** button and its result line are removed from the call drawer.
- The API action (`POST /calls/{id}/executions/refresh`) stays, for the assistant. It has
  no age limit.

## Decisions

Made by Dmytro on 2026-10-09:

- **Remove the button**; look on its own when a mapping changes and in the background
  sync, and stop looking once a call is too old for the backend to still have it.

Proposed by Claude, not yet confirmed:

- **30 days** as the age limit, as a setting. It matches the connected n8n; n8n's own
  default is 14 days, so on a default instance Connexity will ask about some calls that
  n8n has already forgotten, once each.
- 50 calls per background pass.
- A clean lookup that finds nothing is not repeated, unless the tool's mapping changes.

## Done when

- A call stored before its tool was mapped gets its execution after the mapping is
  saved, with no further request from anyone.
- Changing a tool's mapping to another workflow makes its recent calls be looked up
  again.
- The background sync looks up a recent call that has a mapped tool call and has never
  been looked up; a second sync does not ask n8n about it again.
- A lookup that failed because n8n could not be read is tried again later, and not
  before the wait is over.
- A call older than the limit is not looked up automatically, and still is through the
  API action.
- The drawer has no Find executions button and compiles.
- `make check` passes.

## Out of scope

- Reading how long each n8n instance keeps its history, to set the limit per connection.
- Running the API action in the background.
- Looking again for an execution that was found.

## Risks

- **A wrong mapping still finds nothing, silently.** Nothing on the screen now says a
  lookup happened and found nothing. Before, the button's result line did.
- **The first background sync after this merges looks up every recent call with a mapped
  tool**, 50 per pass. For the connected agent that is 13 calls.
- **The retry wait is kept in memory**, per server process, like the one for versions.
- **A reviewer should push back if** removing the only on-screen sign that a lookup ran
  is a loss worth keeping a smaller indicator for.

## Outcome

### Deviations from the plan

- **"Found nothing" is not final until the call has been over for 15 minutes.** The plan
  said a clean lookup that finds nothing is not repeated. Review pointed out that a
  workflow still running when the caller hangs up is saved by n8n a little later, and
  would then never be found. A lookup that leaves a mapped tool call without an
  execution is now repeated on later syncs until 15 minutes after the call ended.
- **One pass per agent at a time**, within a server process. Two at once would look up
  the same calls and collide. Found in review.
- **A pass carries on past a call whose lookup has a problem**, and gives up only after
  three in a row. The plan did not say; the first version stopped at the first problem,
  which let one bad call hold up every older one. Found in review.
- **Tests never reach n8n.** A shared fixture makes the lookup fail by default, the way
  an unreachable backend does; tests about executions supply their own answers.

### Check results

`make check` on this branch:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 1s |
| Backend types (pyright) | ok | 35s |
| Backend tests and coverage | ok | 109s |
| MCP server tests | ok | 4s |
| Frontend lint | ok | 2s |
| Frontend types | ok | 2s |
| Generated client is fresh | ok | 12s |

All steps passed in one run, after the branch was rebased onto `main` once the slice 1.5
pull request had merged. Before the rebase the plan step failed, because the branch then
carried two plan files.

Against the done-when:

| Done when | Result |
|---|---|
| A call stored before its tool was mapped gets its execution after the mapping is saved | Yes |
| Changing a tool's mapping makes its recent calls be looked up again | Yes; a mapping for another tool does not |
| The background sync looks up a recent, never looked-up call once | Yes; a call with only unmapped tools is not asked about |
| A failed lookup is tried again, and not before the wait is over | Yes |
| An old call is not looked up automatically, and is through the API action | Yes |
| The drawer has no Find executions button and compiles | Yes. **Not looked at in a browser** |
| `make check` passes | Yes |

Real calls, on Dmytro's machine, counts only. Local executions were cleared, the two
mapped tools' lookups forgotten (as saving a mapping does), and one background pass run:

| Measure | Result |
|---|---|
| Calls looked up in the first pass | 12 |
| Executions found | 27, all exact matches |
| Time | about 10 seconds |
| Calls looked up in a second pass | 0 |

Twelve, not thirteen as the plan's risk said: one call has since passed the 30-day
limit.

Migration `0007_executions_checked_at` applies, reverses and re-applies on the local
test database, and `alembic check` reports no drift.

**`/code-review`** was run on the diff before the fixes. Four findings, all fixed:

| Finding | Outcome |
|---|---|
| Two passes for one agent could run at once and collide | Fixed |
| A pass stopped at the first problem call, starving older ones | Fixed |
| An execution that finishes just after the call was never found | Fixed |
| Forgetting a tool's lookups loaded whole call rows to clear one column | Fixed: one update |

The review was done by the session that wrote the code, not an independent reviewer.

### Not done

- **Not seen in a browser.**
- **Nothing on the screen says a lookup ran and found nothing**, as the plan's risk said.
  A wrong mapping looks the same as "no execution".
- **The 30-day limit is one number for every n8n.** An instance that keeps less is asked
  about calls it has forgotten, once each.
- **The retry wait and the one-pass-at-a-time rule are kept in memory**, per server
  process. With several processes, two passes can still overlap; the loser's lookups are
  retried after the wait.
- **While a call is under 15 minutes old and has a mapped tool call without an
  execution, every background sync asks n8n about it again.** That is one request per
  mapped workflow per sync.
- The local development database was migrated to `0007` by this session.
