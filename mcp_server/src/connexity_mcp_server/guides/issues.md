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
- **`found_by`:** `code_based` when deterministic code over the call found it, the
  same answer every time; `classifier` when a small model labelled part of the call
  and code turned the labels into the finding; `judge` when a language model read the
  call. A model finding's `detail` names the model. Always tell the person which.
- **`category`:** one of the fixed categories (see `connexity://guides/categories`).
- **Its size:** `calls_affected` of `calls_total`, both in the period. Say "in 11 of
  78 calls".
- **`state`:**
  - `open`;
  - `resolved` (with `resolved_version`, and `fix_live` once that version went live);
  - `reopened`: found again on a call after its fix went live;
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
- **`check`:** the check behind it: what it looks for (`description`), how it decides
  (`kind`), its `version`, what a call's trace must have for it to run (`needs`), and
  for a model check its `provider` and pinned `model`. `detail_fields` says what each
  key of a finding's `detail` means.
- **`setting`:** what the check does for this agent now (`off`, `flags`, `fails`), the
  issue type's default, and when a person last changed it.
- **`versions`:** calls it was found on per agent version, last 30 days, most first;
  `live_version` is the version on the agent's newest call.
- **`findings_all_time`**, **`calls_all_time`:** its size since it was first found.

## Its calls

Call `list_calls` with the `issue_id` (and a `limit`, up to 100, or `cursor` for the
next page) for the calls it was found on, newest first. Each also answers:

- **`agent_version`:** the version the call ran;
- **`issue_findings`:** that issue's findings on the call: the `event_ids` each points
  at (open them with `get_call`), its `detail` (read with `check.detail_fields`), its
  `effect` and the `check_version` that raised it.

## Fixing

1. `get_issue` for everything about it; `list_calls` with the issue for its calls and
   findings; `get_call` for any call in full. Find the cause yourself: Connexity gives
   the facts, not a diagnosis.
2. Propose the change to the person. They approve; you make it, outside Connexity.
3. Once the version with the fix is live, `mark_issue_fixed` with that version.

## Marking fixed

After you change the agent so an issue should stop, call `mark_issue_fixed` with the
issue's `id` and the agent's `version` that carries the fix: its number on the
platform. Add a `note` with what you changed.

- **It becomes resolved** and leaves the open lists. No approval is needed: a wrong mark
  reopens by itself.
- **Connexity waits for that version to go live:** the first real call on it, or on a
  higher number. Until then nothing reopens the issue, because calls still run the old
  version. `get_issue` says "waiting for version 16 to go live".
- **If it happens again** on a call after that, it reopens. The history reads "Came back
  on version 17, after the fix in version 16 went live", and it is on Work again.
- **Refused** when the issue is archived, already marked fixed in that version, or was
  already found on calls of that version or later: then the fix is not in it.
- **There is no confirmation on real calls yet:** "resolved" means nobody has seen it
  since the fix went live.

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
