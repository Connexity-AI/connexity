# Issue page

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Issue page" (10.1, Stage Loop).
- **Design:** `designs/screens/Connexity Issue.dc.html` (Claude Design export) for how
  the page looks. Prompts: `designs/10-issues.md` (the single issue part) and
  `designs/12-adjustments.md` items 1 (Archive) and 8. Where they differ, the screen
  wins.
- **Design:** also `designs/12-adjustments.md` items 27 (affected calls, the Calls page
  issue chip) and 28 (Until it spikes, archiving through the assistant), written
  2026-11-14. Designed in Claude Design and exported 2026-11-14 ("Connexity design review
  (5)"): Issue, Issues, Calls and Action items in `designs/screens/`.
- **MCP:** adds `get_issue(workspace_id, issue_id)`, the same facts as the page, and
  `archive_issue` and `unarchive_issue`, which the assistant calls only after the person
  says yes. `list_calls` gains `issue_id`.

## Goal

A person clicks an issue on the Issues page and sees that one issue:

- how big it is;
- when it started;
- each call it hit, opening the call at that moment;
- how it moved over time, against the agent's versions;
- what was decided about it.

They, or their assistant with their yes, can archive it: a real issue nobody will fix.
Archiving stops it counting from that day, is recorded, and by default undoes itself if
the issue spikes.

From the roadmap: "The single issue page: tiles, occurrences that open the call at the
moment, affected calls over time with version marks, history, and Archive (person
confirms; stops counting; recorded). Issues page rows become clickable. A chain line
shows only the steps that exist now: Found, Fixed in a version."

## What exists today

- **The Issues page** (10.09, Connexity-AI/connexity#197, in review). Its rows open
  nothing. This branch is built on it and is rebased onto `main` once it merges.
- **`GET /issues/{id}`** answers an issue with its findings, newest call first.
  **`PUT /issues/{id}/state`** sets open, resolved (with a version) or archived (with a
  reason), each kept as a decision record.
  - Archiving today has no duration and changes nothing else.
  - No screen and no MCP tool use either route.
- **Each call records the agent version that served it** (`call_component`, kind
  `agent`), so "which version was live on which day" can be read from calls.
- **The single call page** (10.08) has no way to open at a moment from a link.
- **A call's result counts every finding** (Dmytro, 2026-11-13), whatever the issue's
  state.

## Changes

### Backend

**`GET /issues/{id}`** is reshaped to answer the page:

- **The header:** title (check name and key), agent, Critical or Warning, and the state:
  Open, Reopened, "Resolved in version …" or Archived. Archived comes with who archived
  it, when, how long for and why.
- **Tiles:**
  - Calls affected in the last 30 days, "of" the agent's calls in that time;
  - First seen;
  - Last seen.
- **The chain:** two steps, as the roadmap says.
  - **Found** is always done, with the date and the first call's last four digits.
  - **Fixed in a version** is done when the issue is resolved with a version; otherwise
    it reads "Not yet".
  - The other three steps of the design wait for the spec, tests and confirmation.
- **Affected calls per day:** the last 30 days.
  - It has a **version mark** on the first day a call ran on each new agent version
    ("Version 9"), and a mark on the day the issue was archived ("Archived by Alex").
  - The chart shows its time scale, as the design rules require: start and end labels,
    and the peak with its unit.
- **Affected calls:** the latest 10 calls, newest first, one row per call (item 27). Each
  shows:
  - the time;
  - the caller's last four digits;
  - the duration;
  - the call's result;
  - the first moment it happened ("at 2:01"), and "· 2 times" when there was more than
    one.

  Each opens the call at that moment. "All 38 calls" opens the Calls page filtered to
  this issue.
- **History:** the issue's decision records, newest first, with who, when, why and how
  long. It ends with "Opened · first seen on call •••• 2207", read from its first
  finding.

**Archive** (`PUT /issues/{id}/state` with `archived`, and `archive_issue` in MCP):

- **A reason is required** (already true). A **duration** is added: "until it spikes"
  (default) or "forever". It is stored on the issue and in its decision record.
- **A person, or the assistant with the person's yes.**
  - On the web, the signed-in person.
  - Through MCP, `archive_issue(workspace_id, issue_id, reason, duration)`. It is marked
    as a tool that changes data, so assistants ask before calling it. Its rules say:
    name the issue, its size and the duration; wait for the person's yes; put their
    words in the reason.
  - The record says "Archived by your assistant, approved by <person>". Connexity cannot
    prove the person said yes; the hint, the rules and the record are what hold it.
  - `unarchive_issue` works the same way.
- **Hidden while archived, on every call** (Decided, see below):
  - **What is left out:** findings of an archived issue, wherever a call's result, its
    worst finding or its findings are worked out. That covers the Calls page rows and
    tiles, the single call (no mark, no finding), `list_calls` and `get_call`, and any
    later score.
  - **Every call, whatever its date:** a call with only that issue reads Clean.
  - **Still found and stored:** checks keep storing its findings, and the spike rule
    reads them.
  - **When it is unarchived,** by a person, the assistant with a yes, or a spike, every
    call it hit counts again, including those from while it was archived.
  - **One rule, no dates:** "leave out findings whose issue is archived", applied in one
    place in the queries that compute results.
- **"Until it spikes":** the archive undoes itself when the issue starts happening twice
  as often.
  - **The rule:** over the last 7 days it affected at least 3 calls, and at least twice
    its baseline share of the agent's calls. The baseline is its share in the 30 days
    before the archive (any 3 calls when that was 0).
  - **The numbers are stored on the archive** and returned by `get_issue`, so the rule
    can change later without changing what someone agreed to.
  - **When it is checked:** whenever new findings for an archived issue are stored.
  - **What happens:** it becomes Reopened, with the record "Came back: it spiked · 8
    calls this week, twice as often as when it was archived", decided by Connexity. The
    chart gets a "Spiked" mark.
- **Unarchiving** is the existing route (set it to open), plus `unarchive_issue`. The
  design has no unarchive button.

**The Calls page gets an issue filter** (item 27). `GET /calls` and `list_calls` take
`issue_id`.

- They show only calls with a finding of that issue, and the tiles follow it.
- The last column becomes the issue's first moment in that call, with "· 2 times".
- The page shows the issue's title as a chip that can be cleared. It is never a dropdown.

**`get_issue`** answers the same facts for the assistant. Its rules say:

- archiving is a person's decision, made on the issue page;
- give the size as "in N of M calls";
- say whether a rule or a model found the issue.

**`list_issues`** points to `get_issue` in its next steps.

**Migration:** the issue gains its archive's duration (until it spikes or forever) and
the spike rule's numbers fixed at archiving: the baseline share and the minimum calls.
The decision record notes the assistant that acted and the person who approved.

### Frontend

- **Issues page rows become links** to `/issues/{id}`, with the design's hover.
- **The issue page, as the export shows it, without the parts that do not work yet
  (rule 14):**
  - **the page bar:** title, agent, the severity label, the state label and the
    **Archive** button. The button is not shown when the issue is already archived; then
    the "Archived by … · until it spikes · 'reason'" line is shown instead;
  - **the Archive dialog:**
    - a required reason;
    - "How long": Until it spikes (default) or Forever, with their one-line
      explanations;
    - Cancel and Archive;
    - "Only a person can confirm this, here or through your assistant." (item 28);
  - **the three tiles:** Calls affected of N, First seen, Last seen;
  - **Progress:** the chain line with Found and Fixed in a version. Archived shows
    "Stopped: archived on 9 Nov", as in the design;
  - **Affected calls per day:** the chart with its labels, peak and marks;
  - **Affected calls:** the rows and the "All 38 calls" link;
  - **History.**
- **The Calls page, opened from an issue:** the issue chip, the Moment column, and Clear
  keeping the chip (item 27).
- **The single call opens at a moment:** `/calls/{id}?t=102` starts the recording and
  the transcript at 1:42.
- **Left out until their features exist:**
  - the tip (10.13);
  - the Incidents tile, the incident banner and Past incidents;
  - the Milestone tile;
  - the steps In the spec, Tested and Confirmed on real calls;
  - the agent link (there is no agent page);
  - "In Action items" on history lines.

### Docs

- `docs-internal/checks-and-incidents.md`: what "stops counting" means today and the
  spike rule.
- The MCP issues guide gets `get_issue`, and `docs-internal/mcp-architecture.md` lists
  it.

## Decisions

Decided by Dmytro:

- Archive replaces "accepted as known". It needs a reason and a duration. Every archive,
  unarchive and return is recorded (2026-11-12, `12-adjustments.md` item 1).
- An archived issue is hidden on every call, including those before the archive: it does
  not appear in calls, does not make calls fail, does not affect the score, and is
  hidden from the assistant too. It is still found and stored, and when it is
  unarchived, manually or by a spike, its past calls count again. This replaces "stops
  counting from that day; the past is never rewritten" (2026-11-14: "it still found on
  the backend just suppressed for frontend and ai assistant - so if we unarchive it
  manually or through spike past calls count as occurrences"; "yes, hide them too").
- Build only after items 27 and 28 are designed and approved (2026-11-14: "before
  implementing wait for design").
- The assistant can archive through MCP, but it must confirm with the person first
  (2026-11-14: "AI Assistant through MCP can do that as well but need to verify with
  user").
- "Spike" names an issue starting to happen much more often; "escalation" stays for
  handing a call to a person (2026-11-14: "ok i like spike").
- The duration reads "Until it spikes — comes back if it starts happening twice as often
  as now", or Forever. Behind it: twice the baseline share, at least 3 calls in 7 days,
  a 30-day baseline. A spike brings the issue back as Reopened, decided by Connexity
  (2026-11-14: "1. ok 2. ok 3. ok"; "its too heavy math for UI").
- Everything about an issue is counted in calls. The issue page lists affected calls,
  one row per call with "· 2 times", and "All 38 calls" opens the Calls page filtered to
  the issue (2026-11-14, after "we need to show unique issues not occurences").
- The chain shows only Found and Fixed in a version (roadmap entry).
- The design wins over the prompts (roadmap entry).

Proposed by Claude:

- The over-time chart, the tiles and the affected calls cover the last 30 days, as the
  design's "Last 30 days" label says. There is no period picker.
- "Found" is the first finding's call. A version mark is the first call on each agent
  version, read from the calls rather than from when Connexity first saw the version.
- `get_issue` is added for rule 10, though the roadmap entry names only the frontend and
  backend.

## Questions

None open. The design of items 27 and 28 is in `designs/screens/` (export 2026-11-14).

## Done when

- `make check` passes. Backend tests cover:
  - the page answer: tiles, the two chain steps in each state, per-day counts, version
    marks and the archive and spike marks, affected calls with their first moment and
    count, and history;
  - archive:
    - a reason is required;
    - the duration is stored;
    - it is recorded;
    - `archive_issue` and `unarchive_issue` record the assistant and the person who
      approved;
  - while archived, every call's result, worst finding and findings leave the issue out,
    whatever the call's date; after unarchiving, they count again;
  - "until it spikes" comes back at the threshold and not below it, with a 0 baseline,
    with more calls but the same share (no spike), and never for "forever";
  - the Calls issue filter on the web and in `list_calls`;
  - `get_issue`: the same facts, another workspace, not found.
- Played through on a running backend through the API and MCP.
- **For Dmytro to check on screen** (after merge, the demo workspace):
  - an Issues page row opens its issue;
  - the page matches the design minus the parts listed as left out;
  - an affected call opens the call at its moment;
  - "All 38 calls" opens the Calls page with the issue chip and the Moment column;
  - archiving asks for a reason, then shows the archived line, and the issue leaves the
    Open list;
  - dark and light.

## Out of scope

- **Marking an issue fixed** and the "Mark fixed" flow, from the assistant or a person
  (10.15). The chain only shows a resolution already made.
- **Tips** (10.13), **incidents**, **milestones**, the **spec and tests** steps.
- **The assistant proposing an archive** as an Action items card. It archives directly
  with the person's yes instead.
- **An agent page link,** score, reliability and quality charts.

## Risks

- **Archiving and unarchiving change past numbers.** The Calls page tiles and past calls'
  results change on both days. That is the decided intent; the history records each
  change so the jump is explained.
- **The spike check runs inside the call check.** A bug there could reopen issues
  by surprise. Each return is recorded with its numbers, so it is visible and can be
  undone.
- **This branch sits on #197.** If #197 changes in review, this branch is rebased.

## Outcome

### Deviations from the plan

- **Spike window:** the spike rule counts only calls since the archive, inside the last
  7 days. Without that, a busy week just before an archive could bring the issue back on
  its next finding. Found by `/code-review`.
- **Reopening after a fix is now recorded.** A resolved issue found again becomes
  Reopened with a decision record by Connexity ("Found again on a call after it was
  resolved"), so it shows in history. Before, it changed state with no record.
- **The old issue answer is replaced, not kept.** `GET /issues/{id}` answers the page
  (`IssuePagePublic`). `IssueDetailPublic`, `IssueFindingPublic` and
  `crud.list_issue_findings` are deleted; nothing else used them.
  - **One test changed for it:** in `test_issues.py`, the issue test checks
    `affected_calls` instead of `findings`, and the resolve test expects the new
    reopened record next to the person's.
- **Archiving an archived issue through MCP changes nothing** and says so. To change its
  duration, the assistant unarchives and archives again. Found by `/code-review`.
- **The Calls answer carries the issue's title** (`issue`) for the chip, so the page
  needs no second request.
- **Storage:** archive data is three issue columns (`archived_at`,
  `archive_until_spike`, `archive_baseline_share`). Decision records gain
  `assistant_name` and `detail`, which holds the duration, baseline and spike numbers
  (migration `0019`). Issues archived before this migration count as "forever".
- **Who the history names:** the person's name, or the first part of their email.
  Connexity's own decisions name no person. Through MCP, the assistant is recorded by
  its registered name, or "your assistant" when it has none.

### Check results

`make check` on the final tree. `pnpm build` also succeeds, with `/issues` and
`/issues/[id]` among the routes.

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

**New tests in `test_issue_page.py` (10):**

- the page:
  - title, tiles and the chain (found, then fixed in a version);
  - 30 days with the peak;
  - a version mark only for a change;
  - affected calls with their moment and "2 times";
  - history ending with Opened;
- archiving hides the issue on every call, before and after the archive, on the single
  call and the Calls page, and unarchiving brings back every call's result;
- a spike at the threshold and not below it, with the record, history and marks;
- more calls at the same share is no spike;
- "forever" never comes back, and a zero baseline spikes at 3 calls;
- calls from before the archive never make a spike;
- the Calls page issue filter with moments and the chip's title;
- MCP:
  - `get_issue`, `archive_issue` and `unarchive_issue`, with the person recorded;
  - hidden from `get_call` while archived;
  - `list_calls` with `issue_id`;
  - another workspace and an unknown id;
- archiving an archived issue through MCP changes nothing;
- another workspace can neither read nor archive.

**MCP server:** the three tools are listed with their hints (they change data, are not
destructive and stay inside Connexity). `archive_issue` sends its reason and duration;
`list_calls` sends `issue_id`.

**Migration `0019`:** applies on the local database (upgrade from `0018`), and
`alembic check` is clean in the test run.

**Played through on a running backend** (port 8027, local database). The throwaway agent
had 21 invented calls:

- 20 calls 10 to 20 days ago on version 7, two with missing booking details;
- one call 3 days ago on version 8, with missing details twice and a double booking;
- three more calls added during the run.

| # | Request | Came back |
|---|---|---|
| 1 | `GET /issues/{id}` | 200; calls affected 3 of 21; found yes, fixed none; 30 days, peak 2; mark "Version 8"; 3 affected calls, the first "2 times"; history: opened |
| 2 | `GET /calls?issue_id=…` | 3 calls, tiles 3, the chip's title, moments 2, 1, 1 |
| 3 | The call's screen before archiving | Failed, 3 findings |
| 4 | Archive without a reason | 422 |
| 5 | Archive until it spikes | 200, archived |
| 6 | That call's screen while archived | Failed, 1 finding: the double booking, a second issue, still shows |
| 7 | `GET /issues/{id}` archived | duration until_spike; marks version and archived; history archived, opened |
| 8 | Three new calls with the issue, then the page | Reopened; "Came back: it spiked", by Connexity, "3 calls this week, 7 times as often as when it was archived"; marks version, archived, spiked |
| 9 | MCP `get_issue` | 200, 6 calls, guide `connexity://guides/issues` |
| 10 | MCP `archive_issue`, forever | 200, archived, by the person, assistant "your assistant" |
| 11 | MCP `get_call` while archived | 1 finding (the other issue) |
| 12 | MCP `unarchive_issue` | 200, open |
| 13 | MCP `list_calls` with `issue_id` | 6 calls |
| 14 | MCP `get_issue`, unknown id | 404 |
| 15 | `GET /issues/{id}`, not signed in | 401 |
| 16 | `GET /calls?issue_id=x` | 422 |

The backend log had no errors. The throwaway users, workspaces, agents, calls, issues
and records were deleted afterwards.

**`/code-review` (high) raised six findings:**

- **Fixed:** the spike window counted calls from before the archive.
- **Fixed:** re-archiving through MCP claimed a change that did not happen.
- **Fixed:** the Calls affected tile counted a partial first day the chart does not show.
- **Fixed:** moments loaded every event of every call.
- **Not fixed:** the Calls page filtered to an archived issue shows its calls as Clean
  next to their moment. That is the hide-everywhere rule as decided.
- **No change needed:** the Archive dialog is a popover anchored to its button, as the
  design draws it, not one of the app's dialogs.

**For Dmytro to check on screen** (app.connexity.ai after merge, the demo workspace):

1. **Issues page:** a row opens its issue, with a hover.
2. **The issue page** in dark and light, against the export of 14 Nov:
   - back arrow, title, agent, Critical or Warning, the state chip and Archive;
   - three tiles: Calls affected of N, First seen, Last seen;
   - Progress: Found (with the first call, which opens) and Fixed in a version;
   - Affected calls per day: 30 bars with 0, middle and top labels, day labels every
     week, and marks;
   - Affected calls: one row per call with "at 2:01 · 2 times", opening the call at
     that moment;
   - "All N calls";
   - History.
3. **Archive:**
   - a reason is required, and Until it spikes is the default;
   - after Archive, the archived line shows under the bar and Progress reads "Stopped:
     archived on …";
   - the issue leaves the Open list;
   - the calls it hit no longer show it.
4. **The single call** opened from an affected call starts at that moment.
5. **"All N calls"** opens Calls with the issue chip and a Moment column. × removes the
   chip, and Clear keeps it.
6. **Not shown, as planned:** tip, incidents, milestone, the agent link, and the spec,
   tests and confirmation steps.

### Not done

- **The tip** (10.13), **incidents**, **milestones**, the **spec and tests** steps of
  the chain, and an **agent link**: their features do not exist.
- **Unarchiving on screen:** the design has no button. It works through the API and
  MCP.
- **The assistant proposing an archive in Action items:** Action items does not exist.
  The assistant archives with the person's yes instead.
- **A loading skeleton** for the page, as on the Calls and Issues pages.
- **The screens were not looked at by the session.**
