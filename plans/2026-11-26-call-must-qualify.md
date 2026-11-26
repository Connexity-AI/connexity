# A call must qualify before it is judged against the spec

- **Owner:** Dmytro
- **Slice:** Roadmap 105.11, "A call must qualify before it is judged against the spec"
- **Design:** Call screen and Calls list: a "Not graded" result and its explainer.
  Prompt `designs/23-not-graded.md`; approved by Dmytro 2026-11-26 (Claude Design
  export "Connexity design review (23)", whose `Connexity Call.dc.html` and
  `Connexity Calls.dc.html` replace those in `designs/screens/`).
- **MCP:** `get_call` and `list_calls` answer whether a call is graded and why not;
  `list_calls` takes `not_graded` as a result filter. Both contract entries in
  `mcp_server/.../contract.py` and their input descriptions are updated.

## Goal

A call where the agent spoke fewer than 10 words is not graded: it will never be judged
against the spec (roadmap 105.15), and it cannot lift the score by looking like a call
that passed. The call screen, the Calls list and the assistant all say so, and why.

Why (from the 2026-11-26 lab test, one agent, 50 calls): on calls where almost nothing
is said, any verdict is noise. The classifier flagged "introduce yourself" on calls where
the agent got out one to five words. Seconds are the wrong measure: a 5-second call can
hold a real break, a 13-second call one word.

On the hosted database today, 443 of 1,128 stored calls (39%) are under the floor: 15
where the agent said nothing, 428 where it said 1 to 9 words.

## Changes

**What qualifies (Decided, Dmytro 2026-11-26).**

- A call qualifies when the agent's utterances hold 10 words or more in total. Words are
  counted in the agent's transcribed text only (speaker `agent`), split on whitespace.
  Caller and `other` speakers do not count.
- No exception by kind of call: voicemail and call screeners are graded when the agent
  is above the floor.

**Data.**

- Each call stores `agent_words` (Proposed), counted when its trace is stored or
  replaced. Calls already stored get it from their events in the migration, so nothing
  needs re-ingesting.
- The floor is one constant in the backend (`GRADING_MIN_AGENT_WORDS = 10`), not a
  setting.

**A call's result.** Today a call is failed, degraded, clean or unchecked. A new
result, **not graded**, is added.

- A call under the floor with no shown finding is not graded instead of clean or
  unchecked; a call
  under the floor that a code check failed or flagged keeps that result, and still says
  it was not judged against the spec.
- Every place that works out a call's result reads it the same way
  (`call_check_statuses` and the Calls list's SQL filters), so the call screen, the Calls
  list, its tiles, `list_calls`, `get_call` and the score never disagree.

**Score.** A not graded call is not a checked call: it is left out of the score's
counts, as unchecked calls are today. So a short call with nothing found no longer
counts as clean.

**Call screen and Calls list (after the design).**

- The call screen shows that the call was not graded and why: "Not graded: the agent
  spoke fewer than 10 words."
- The Calls list shows "Not graded" as the result, has it as a result filter and counts
  it in the tiles.
- Exactly how is in the design prompt; the build follows the approved design.

**MCP.**

- `get_call`: `graded` (true or false) and, when false, `not_graded_reason` ("the agent
  spoke fewer than 10 words") and `agent_words`. A rule in the answer: a call that is not
  graded is never judged against the spec and does not count in the score; do not raise
  clarifications or fixes from it.
- `list_calls`: each row's result can be `not_graded`; the `result` filter accepts it.

**Docs.** `docs-internal/checks-and-incidents.md` (a call's result, and the score) and
`docs-internal/metrics.md` if it defines checked calls.

## Decisions

1. **The floor removes only the positive.** Decided, Dmytro 2026-11-26 (chose "Only
   remove the positive"). Code checks still run on every call. A short call with a
   code-check finding (a tool failed) keeps failed or degraded and counts in the score,
   because the failure is real. A short call with nothing found is not graded and left
   out of the score. The spec check (105.15) skips every short call.
2. **One pull request.** Decided, Dmytro 2026-11-26 (chose "One PR"). Backend and MCP
   are built first, while the design prompt runs in Claude Design; the screens join the
   same pull request once the design is approved.
3. **The floor counts agent words only, any kind of call.** Decided, Dmytro 2026-11-26.
4. **10 words.** Decided, Dmytro 2026-11-26.
5. **Not graded calls do not count in the score.** Decided, Dmytro 2026-11-26 ("we need
   to have ignored calls / non relevant so they will not affect the score in positive
   way").
6. **The word count is stored on the call, backfilled in the migration.** Proposed.
7. **An issue's share of an agent's calls** (Issues page, spike detection) keeps all of
   the agent's stored calls as its base. Proposed: changing that base would move
   archived issues' spike baselines, which were fixed when they were archived.

## Done when

- A call stored with 9 agent words and no finding is `not_graded` in `get_call`,
  `list_calls` and the Calls list tiles, and is not in the score's counts.
- A call with 10 agent words and no finding is clean, as today.
- A call with 3 agent words and a failed tool call is
  failed, counts in the score, and `get_call` says it was not judged against the spec.
- Caller words do not count: a call where the caller speaks 50 words and the agent 4 is
  not graded.
- Calls stored before the migration have `agent_words` from their events.
- The `list_calls` and `get_call` contract entries describe the new fields and filter,
  and the contract tests pass.
- The call screen and Calls list match the approved design.

## Out of scope

- The spec check itself (105.15), which is the check that will skip calls under the
  floor.
- Any change to what code checks run on.
- Making the floor a setting per agent or workspace.
- Reliability's "calls that never connected or reached voicemail" exclusion, which is
  unchanged.

## Risks

- 39% of stored calls change result, so the score moves for every workspace when this
  merges. A score that drops or rises on the day of the release should be expected,
  not read as a regression.
- Counting by whitespace miscounts transcripts with odd spacing or numbers written as
  digits ("10:30" is one word). Close enough for a floor of 10.
- A trace replaced later (a re-read for late analysis) must recount `agent_words`; a test
  covers it.

## Outcome

### Deviations from the plan

- **Not graded replaces clean only, not unchecked.** The plan said "instead of clean or
  unchecked"; the approved design turns only a short call that would be clean into Not
  graded. A short call whose checks have not run stays unchecked, because a code check
  may still find a real failure on it. The build follows the design.
- **Unchecked has its own tile and a pill in the Calls list,** as in the approved
  design (six tiles: Calls, Failed, Degraded, Clean, Not graded, Unchecked). Before, the
  page showed four tiles and Unchecked as plain text. `NumberTile` gains an optional
  neutral `icon` for these two tiles.
- **The Dashboard's areas leave out short calls** (from `/code-review`): an area is
  healthy only when its check ran on at least one graded call, so short calls cannot
  turn an area green, for the same reason they cannot lift the score.
- **The agent page's Calls tab** reuses the Calls list, so it shows the six tiles and
  the Not graded result too. The Agent Profile design export was not updated for it.
- **The issue page's affected calls** show "Not graded" as plain text when that is a
  call's result (only possible on an archived issue, whose findings are hidden). The
  Issue design has no such state.
- **The floor is written once.** Field descriptions and MCP rules are built from
  `GRADING_MIN_AGENT_WORDS` (from `/code-review`).
- **Existing tests' invented calls got a longer agent line.** Several test helpers had
  the agent say one or two words ("Hello", "One moment"), so their clean calls became
  Not graded. The helpers now give the agent a sentence of 10 words or more; no
  assertion was loosened.

### Check results

`make check`, once, after this Outcome was written:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Start local database | ok | 0s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 10s |
| Backend tests and coverage | ok | 346s |
| MCP server tests | ok | 5s |
| Frontend lint | ok | 2s |
| Frontend types | ok | 1s |
| Generated client is fresh | ok | 10s |

No separate play-through server: the route tests send the same requests through the
API (`TestClient` on the local database): `list_calls` with and without the
`not_graded` filter, its tiles, `get_call` on a short, a short failed and a graded
call, the score's counts, a trace stored again, and the migration's backfill run on
stored calls.

**For Dmytro to check on screen:**

1. **Calls:** six tiles, the last two Not graded and Unchecked with their icons and
   neutral numbers. Calls where the agent said almost nothing (voicemail cut off,
   hang-ups) read "Not graded" in the Result column, in the neutral pill. The Result
   filter has "Not graded" between Clean and Unchecked and narrows the list without
   changing the tiles.
2. **A Not graded call:** the "Not graded" pill next to the title, and under the title
   the line "Not graded: the agent spoke fewer than 10 words. It isn't judged against
   the spec and doesn't count in the score."
3. **A short call that failed** (a tool error before the agent said much): Failed next
   to the title, and the same explainer line.
4. **A normal call:** no explainer line, result as before.
5. **Dashboard and an agent's page:** the score moves, because short calls with nothing
   found no longer count as clean (39% of stored calls on the hosted database are under
   the floor).
6. **An agent's Calls tab:** the six tiles, as on Calls.

### Not done

- The Agent Profile and Issue design exports do not show Not graded (see Deviations);
  they need a pass in Claude Design.
- Not checked on the hosted database after the migration; the backfill was tested on
  invented calls in the test database.
