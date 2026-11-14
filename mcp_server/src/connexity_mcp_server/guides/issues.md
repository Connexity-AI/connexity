# Issues

An issue is one problem found on an agent's real calls: every call where Connexity's
checks found the same thing. Call `list_issues` with a `workspace_id`. It answers the
same issues and counts as the Issues page.

## Finding issues

- **`query`:** words in the title, or a whole issue id.
- **`agent_id`**, **`category`** (a key from `list_categories`), **`severity`**
  (`critical` or `warning`).
- **`status`:** `open` by default, which includes reopened; or `reopened`, `resolved`,
  `archived`.
- **`period`:** `7d`, `30d` (default) or `90d`. Open and reopened issues show whatever
  the period. A resolved issue shows only if it was resolved in the period. Archived
  issues always show under their status.

Issues come worst first: open or reopened Critical issues and reopened ones, then the
other open ones, then by calls affected in the period.

`tiles` counts Open, Critical, Reopened, Resolved in the period, and Calls affected of
all calls in the period. The tiles follow `agent_id` and `period` only, never the search
or the other filters.

## Each issue

- **`severity`:** `critical` when its check fails the call, otherwise `warning`. Each
  check has a default; a person can change it per agent.
- **`found_by`:** `rule` when deterministic code over the call found it, the same
  answer every time; `model` when a classifier or judge did. Always tell the person
  which.
- **`category`:** one of the fixed categories (see `connexity://guides/categories`).
- **Its size:** `calls_affected` of `calls_total`, both in the period. Say "in 11 of
  78 calls".
- **`state`:**
  - `open`;
  - `resolved` (with `resolved_version` when one was given);
  - `reopened`: found again on a call that started after it was resolved;
  - `archived`: real, and nobody will fix it. Only a person archives, with a reason.

## One issue

Call `get_issue` with an issue's `id`. It answers, for the last 30 days:

- **`tiles`:** calls affected of the agent's calls, first and last seen.
- **`chain`:** when it was found and on which call, and whether it is fixed in a version.
- **`days`:** calls per day, with `marks` for each new agent version, an archive and a
  spike, and the `peak`.
- **`affected_calls`:** the latest 10 calls, one per call, each with its `moment` (when
  it first happened and how many times). `list_calls` with `issue_id` lists them all.
- **`history`:** every decision, newest first, ending with when it was opened.
- **`archive`:** while archived, who archived it, when, how long and why.

## Archiving

Archive an issue nobody will fix with `archive_issue`; `unarchive_issue` brings it back.

- **It is the person's decision.** First tell them which issue, its size and the
  duration. Call the tool only after they say yes, with their words as the `reason`. The
  record says "your assistant, approved by <them>".
- **`duration`:** `until_spike` (the default) brings it back as reopened if it starts
  happening twice as often as now: at least 3 calls in 7 days and twice its share of the
  agent's calls. `forever` stays archived until someone unarchives it.
- **While archived** it is hidden on every call, including earlier ones, and counts for
  nothing. Unarchived, all its calls count again.

## How to talk about them

- Lead with the critical ones and their size, grouped by category.
- Say how each was found.
- Do not quote callers or tool arguments unless the person asks about one call.
- Calls are checked within a minute of arriving, and every stored call is checked when a
  check is added or changes.
