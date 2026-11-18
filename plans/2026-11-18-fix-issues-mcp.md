# MCP for fixing issues

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "MCP for fixing issues" (10.16). Builds on
  Connexity-AI/connexity#225 (10.14, the check system, merged 2026-11-18).
- **Design:** No UI change.
- **MCP:** extends `get_issue` and `list_calls`, and the issue-fix task's steps in
  `get_next_task`. No new tool (rule 10: extend a tool before adding a near-duplicate).

## Goal

The assistant gets every detail Connexity has about an issue in one `get_issue` call,
and the calls it was found on, with what was found in each, from `list_calls`, as many
as it asks for. It picks its own tools from there: Connexity does not hand it a
digest or advice.

## Decisions

- **Accept, build** (Dmytro, 2026-11-18).
- **Send all details about the issue; a separate call returns the affected calls, with
  an optional limit. "Our goal is not to spoonfeed AI as it smart enough to chose its
  own tools"** (Dmytro, 2026-11-18).
- **No verification yet** (Dmytro, 2026-11-18: "We dont work on verification yet").
  `mark_issue_fixed` and the test tools stay as they are. This drops the roadmap row's
  "the answer's next steps tell it to verify the fix by running ... scenarios".
- **The tip is parked** (Dmytro, 2026-11-17).
- **The affected calls come from `list_calls` with `issue_id`, extended,** rather than a
  new tool: it already lists exactly those calls, paginated, with `limit` (Proposed,
  rule 10).

## What exists

- **`get_issue`**: title, key, agent, category, severity, `found_by`, state, size over
  30 days, first and last seen, the fix chain, calls per day with version marks, the
  latest calls with their moment, history.
- **`list_calls` with `issue_id`**: only that issue's calls, newest first, paginated
  (`limit`, `cursor`), each with its moment (when it first happened, how many times).
  Nothing about what was found.
- **`get_call`**: one call's whole timeline and findings.
- **`get_next_task`**'s issue-fix steps still say "the person resolves the issue",
  which 10.13 changed: the assistant marks it fixed with `mark_issue_fixed`.

## Changes

### `get_issue`: every detail about the issue

- **The check behind it:** its type, title, description, kind (`found_by`), version,
  and for a model check its provider and pinned model.
- **What its findings carry:** the detail fields this check writes and what each means
  (for `tool_call_failed`: the tool's status; for `booking_details_missing`: which
  arguments were empty; for `action_claimed_without_tool`: the action, the model's
  probability, why, the model). Written beside each check, in its file.
- **Its setting for the agent:** off, flags or fails the call, and since when.
- **Versions involved:** affected calls per agent version in the last 30 days, and the
  version live now.
- **Finding counts:** how many findings and calls in all, not only the last 30 days.
- **Kept as is:** size, the fix chain, calls per day, history. The latest-calls list
  stays short; `list_calls` has the rest.

### `list_calls` with `issue_id`: the affected calls

- **Each call also answers its findings of that issue:** the events each points at, the
  finding's detail, its effect (flags or fails), and the call's agent version.
- **`limit` is optional,** as today (default and maximum as for any `list_calls`).
- **Without `issue_id`, nothing changes.**

### `get_next_task`: the issue-fix steps

- **Corrected to today's loop:** `get_issue`, then `list_calls` with the issue for its
  calls, `get_call` for any call in full; propose the change to the person; once the
  change is live, `mark_issue_fixed` with that version.

### Docs

- `mcp_server/.../guides/issues.md`: what `get_issue` and `list_calls` with an issue
  answer, and the fix loop.

## Done when

- Through the API on the local database, with invented calls:
  - `get_issue` on a code-based issue answers the check's description, kind, version,
    detail fields, setting, calls per version and total counts;
  - on a classifier issue it also names the provider and the model;
  - `list_calls` with `issue_id` and `limit` 2 answers two calls with their findings'
    events, detail, effect and version; without `issue_id` the answer is unchanged.
- `get_next_task`'s issue-fix steps name `list_calls` and `mark_issue_fixed`.
- `make check` passes.

## Out of scope

- Verification after a fix (not yet, Dmytro).
- Tips (parked).
- Anything that changes an agent.

## Risks

- **A finding's detail is only as useful as the check makes it.** Each check documents
  its fields; a check with thin detail sends the assistant to `get_call`.

## Outcome

### Deviations from the plan

- **Each check documents its finding detail** in a new `detail_fields` on the check
  (`checks/base.py`), and a test fails for a check without it.
- **`setting.since`** is when a person last changed the check for the agent; it has
  no "reason", which stays in the issue's history.
- **`live_version`** is the version on the agent's newest call, as written; during a
  rollout that may still be the older version.
- **With `issue_id` of an archived issue,** `list_calls` lists that issue's own
  findings; its rules now say so (other calls still hide archived findings).
- **The `get_next_task` step test** calls the step builder directly rather than going
  through `get_next_task`.

### Check results

`make check` (before the review fixes):

| Step | Result |
|---|---|
| Plan present and complete | failed: Outcome not yet written (this section) |
| Start local database | ok |
| Backend lint and format | failed: one import order in the new test; fixed |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok (new: `test_mcp_fix_loop.py` 4) |
| MCP server tests | ok (47; `list_calls` with the issue's new fields) |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

After the fixes: lint, pyright and the affected tests (`test_mcp_fix_loop.py`,
`test_mcp_issues.py`, `test_issue_types_doc.py`, 11) pass, and the client was
regenerated; the whole `make check` was not run again.

**`/code-review` (high), 6 findings:** fixed three (archived issue's findings now
matched by the rules, `JsonValue` instead of `Any` for a finding's detail, a test that
every check documents its detail); one was not a bug (`live_version` is documented as
the newest call's version); two skipped (the step test calls a private helper; every
call item is copied once per `list_calls`, cheap).

No separate play-through server: the route tests send the same requests through the
API on the local database.

### Not done

- **Not checked against the hosted data:** the new answers were tried on invented calls
  only.
- **The roadmap row** for 10.16 is set to Done only after merge.
