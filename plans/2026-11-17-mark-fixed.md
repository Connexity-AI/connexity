# Mark fixed, reopen on recurrence

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Mark fixed, reopen on recurrence" (10.13).
  It comes after the Tests tab (10.1294, #223, not merged yet).
- **Design:** `designs/10-issues.md` (statuses Open, Reopened, Resolved in a version,
  Archived), `designs/12-adjustments.md` items 1 and 28, and
  `docs-internal/checks-and-incidents.md` ("Resolved", Decided 2026-11-12).
- **MCP:**
  - a new tool, `mark_issue_fixed`;
  - `get_issue` and `list_issues` say when a fix went live and when an issue came back
    after one.

## Goal

When the assistant fixes an issue, it marks it fixed in the version that carries the
fix. The issue becomes Resolved and leaves the open lists. Connexity watches for that
version to go live on real calls. If the issue happens again on a call after that, it
reopens. The assistant learns it through MCP and on Work, and starts again. There is no
confirmation on real calls yet: gating and tests improve this later.

## Decided

- **Resolved:** the assistant or a person marks an issue fixed, linked to the version
  that carries the fix. If it happens again on a call that started after that, it
  reopens. Reopened replaces "regressed" (Dmytro, 2026-11-12, `checks-and-incidents.md`).
- **From the roadmap row:** "it becomes Resolved, linked to the agent version that
  carries the fix once Connexity sees it go live … No confirmation on real calls; gating
  and tests improve this later. Issue states exist from slice 2.3: review and rename."
- **The assistant can do anything a person can; critical actions need the person's
  approval** (`testing.md` decision 7). Marking fixed is not one of them: a wrong mark
  reopens by itself.

## What exists (slice 2.3)

- **The states** are open, resolved, reopened and archived, already under the
  2026-11-12 names.
  - "Regressed" survives only in one code comment.
  - "Accepted as known" is gone.
- **`PUT /issues/{id}/state`** resolves with an optional free-text version. It records
  `resolved_at`, the moment of marking, and `resolved_version`, and keeps a decision
  record.
- **Reopening:** a new finding reopens a resolved issue when its call started after
  `resolved_at`. That is the moment of marking, not the moment the fix went live.
  So a call on the old version, a minute after the assistant marked the issue fixed
  in a version not yet published, reopens it wrongly.
- **MCP** has `archive_issue` and `unarchive_issue`, but nothing to mark an issue fixed.
  `list_issues` filters by `reopened` and `resolved`.
- **The screens:**
  - the Issues and issue pages show "Resolved in version 15" and "Reopened";
  - the issue page's history lists each state change;
  - no button marks an issue fixed.
- **Work** drops an issue's fix task once the issue is resolved, and shows Reopened.
- **Calls** carry the agent's version (`call.agent_version`), as Retell numbers it.
- **Hosted data:** 3 issues, all open, none resolved.

## Changes

### Marking fixed

- **`mark_issue_fixed(workspace_id, issue_id, version, note?)`:**
  - the version is required (question 1); the note is optional;
  - the issue becomes Resolved in that version and leaves the open lists;
  - a decision record reads "Marked fixed in version 16 by your assistant", with the
    person the session belongs to.
- **Refused** (question 3) when:
  - the issue is archived (unarchive it first);
  - it is already resolved in that version;
  - it was already found on calls of that version. Then the answer reads "This issue
    was found on 4 calls on version 16; the fix is not in it", and nothing changes.
- **The web route** keeps resolving with or without a version. Without one, the fix
  counts from the moment of marking, as today.

### Going live (question 2)

- **The issue gains `fix_live_at`:** the start of the first real call on the fixed
  version, or on a higher version number when both are numbers.
- **It is set as calls are checked,** for every resolved issue of the agent waiting for
  that version. When the version already had calls before the issue was marked fixed,
  the earliest of them counts.
- **Simulated calls never count:** they are not `call` rows.
- **A decision record by Connexity:** "Version 16 went live".

### Reopening

- **A resolved issue reopens** when it is found on a call that started at or after
  `fix_live_at`. For a fix with no version, the time is `resolved_at`.
- **While the fix is not live yet,** findings on calls never reopen it: those calls run
  the old version.
- **The reopening record reads** "Came back on version 17, after the fix in version 16
  went live".
- **The fix stays recorded** (`resolved_version`, `fix_live_at`) when the issue
  reopens, so the history keeps both.

### MCP

- **`get_issue`** answers `fixed_in`, `fix_live_at` and the reopening line. Its next
  steps:
  - resolved and not live: "Waiting for version 16 to go live";
  - reopened: "It came back after the fix in version 16: read the new calls and fix it
    again, then `mark_issue_fixed` with the new version".
- **`list_issues`' rows** carry the same `fixed_in` and `fix_live`.
- **The issues guide** gains "Marking fixed".

### Screens (question 4)

- **No button:** the person asks their assistant, as the CLAUDE.md "Do not add" list
  says for what the assistant can do through MCP.
- **The status label stays "Resolved in version 16".** The issue page's history shows the
  new records in the style its lines already have:
  - "Marked fixed in version 16 by your assistant";
  - "Version 16 went live";
  - "Came back on version 17".

### Review and rename

- **The leftover "regresses" comment** becomes "reopens".
- **`docs-internal/checks-and-incidents.md`:** "Resolved" now says the fix counts from
  when its version goes live.

## Decisions

- Everything under "Decided" is Decided.
- **Questions 1 to 4 are Decided as recommended** (Dmytro, "Accept, build",
  2026-11-17).

## Questions

1. **The assistant names the version.** Recommend `version` is required in
   `mark_issue_fixed`, so a fix always waits for its version. The assistant knows it: it
   made the change. The alternative is optional, counting from the moment of marking as
   the web route does.
2. **When a version is live.** Recommend: the first real call on that version, or on a
   higher number when both are numbers, as Retell's are. The alternative is the exact
   version only. That misses a fix that went live inside a later version, and the issue
   would never be watched.
3. **Refuse a fix in a version that already shows the issue.** Recommend refusing, with
   the count, so a wrong claim is caught at once. The alternative is to mark it and
   warn; the issue then reopens on the next such call.
4. **No screen change beyond history lines.** Recommend keeping "Resolved in version
   16" and adding the new lines to history, with no design adjustment, since they
   follow the history lines already designed. The alternative is a design adjustment
   that shows "Not live yet" in the status label.

## Done when

- **Through the API,** in route tests on the local database:
  - `mark_issue_fixed` resolves with the version and its record;
  - each refusal changes nothing;
  - a call on the old version after marking does not reopen the issue;
  - the first call on the fixed version (or a higher number) sets `fix_live_at` and
    records it;
  - a later finding reopens with its line;
  - a version that was live before marking counts from its first call;
  - a fix without a version keeps today's rule;
  - `get_issue` and `list_issues` answer the fix and the steps.
- **`make check` passes** once, before the pull request.
- **For Dmytro on screen:** an issue's history after it was marked fixed, went live and
  came back.

## Out of scope

- Confirming a fix on real calls ("Confirmed on real calls" in the chain) and fixes
  proven by tests: gating and tests improve this later.
- Gate issues (Milestone 7).
- A button for people to mark an issue fixed.

## Risks

- **Version numbers that are not numbers** (other platforms) only match exactly. A fix
  that goes live in a later version of such a platform is not seen, and the issue never
  reopens. It shows "Waiting for version … to go live" on `get_issue`, so the assistant
  sees it.

## Outcome

### Deviations from the plan

- **Branched from `main`,** not from the Tests tab (#223, open). Nothing here depends
  on it.
- **The migration keeps old fixes as they were:** a fix already marked in a version
  counts from when it was marked (`fix_live_at = resolved_at`). The hosted database had
  none.
- **A fix marked in a version that is already live** records "Version 16 went live" at
  once, after "Marked fixed in version 16".
- **The history's "by" for a fix the assistant marked** reads "by your assistant". Fixes
  need no approval, unlike archiving, so not "approved by …". The only frontend change
  is in `issue-view.tsx`.
- **The test helper `_call` in `test_mcp_issues.py`** takes an optional version.
- **Review findings, both left as they are:**
  - going live costs one small query per checked call (skipped);
  - the web route still resolves without the version checks; no screen uses it to
    resolve (no change needed).

### Check results

`make check`:

| Gate | Result |
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

While building, only the touched test files ran:
- `test_mark_fixed.py` (new), `test_issues.py`, `test_issues_list.py`,
  `test_mcp_issues.py`, `test_issue_page.py`, `test_work_page.py`, `test_next_task.py`,
  `test_question_cards.py`, `test_checks.py`, the check services' tests and
  `app/tests/crud`;
- the MCP server tests.

No separate play-through server: the route tests send the same requests through the API
on the local database.
- **`mark_issue_fixed`:**
  - resolves in version 16 with "Marked fixed in version 16" and the note;
  - the issue leaves the open list;
  - `get_issue` says it waits for version 16.
- **Calls on version 15** after the mark do not reopen it. A clean call on version 16
  makes the fix live: "Version 16 went live", `live_at`, `fix_live` in the list.
- **Found on version 17,** it reopens: "Came back on version 17, after the fix in version
  16 went live", with a next step to fix it again and `mark_issue_fixed`. Marking it
  fixed in version 18 works.
- **Refusals change nothing:**
  - a version it was found on ("found on 1 call on version 15");
  - the same version twice;
  - an archived issue;
  - another workspace (404);
  - an empty version (422).
- **The web route:**
  - a fix in a named version waits for that version;
  - a fix already live counts from its first call;
  - a fix with no version counts from when it was marked;
  - the Issues list counts the first call on the fixed version as live, and reopens on
    it.

Two existing tests changed with the rule:
- `test_issues.py`'s "regresses only on a call that started afterwards" became
  "reopens only after its fix goes live". It now also checks that a call on the old
  version after the mark does not reopen the issue.
- `test_issues_list.py` resolves in version "15" and reopens on a call on version 15.

Nothing was weakened.

**For Dmytro to check on screen.** On an issue the assistant marked fixed, its history
on the issue page reads:
1. "Marked fixed in version 16 by your assistant, 17 Nov · 'note'";
2. "Version 16 went live by Connexity, …";
3. after it came back, "Reopened by Connexity, … · 'Came back on version 17, after the
   fix in version 16 went live'".

The Issues page shows it under Resolved, then under Reopened.

### Not done

- Confirming a fix on real calls ("Confirmed on real calls" in the chain); tests and the
  gate improve this later.
- A screen button to mark an issue fixed: the person asks the assistant.
