# Calls

Every call of the workspace's added agents, checked as it arrives. Call `list_calls`
with a `workspace_id`.

- **Newest first,** a page at a time (`cursor`, `limit`), with tiles for the filters and
  period: calls, failed, degraded, clean and unchecked. The tiles ignore the result
  filter, so they always add up.
- **Find a call:** pass `query`. A phone number, whole or its last digits, matches the
  end of the caller's number ("4821" or "+1 732 555 4821"). Anything else must be a whole
  call id: Connexity's or Retell's.
- **Filters:** `agent_id`, `result` (failed, degraded, clean, unchecked), `category` (a key
  from `list_categories`) and `period` (7d, 30d or 90d; 30d by default).
- **One issue's calls:** pass `issue_id` (from `list_issues`). Each call then has its
  `moment`: when the issue first happened in it and how many times.
- **Archived issues are hidden:** their findings never make a call failed or degraded and
  are never its worst finding, until the issue is unarchived.
- **Each call** has its time, agent, the caller's last four digits (never the number),
  duration, result and worst finding: the check's title, what broke (`key`), its
  category, severity and whether a rule or a model found it.

Results: **failed** when a finding fails the call, **degraded** when one only flags it,
**clean** when checks ran and found nothing, **unchecked** when none could run.

## Many calls in full

Call `read_calls` when you need to look across calls yourself: how often a tool was
called with an empty argument, what callers ask for first, where conversations stall.
It takes exactly `list_calls`' filters and answers each call's conversation in order: a
turn has `speaker` and `text`; a tool call has `tool`, `status`, `arguments` and
`result`. Each call also has its result, agent version and what the checks found.

- **It is a page, not all of them.** A page holds as many calls as fit in one answer,
  usually 10 to 15 and at most 50, and can hold fewer than `limit`. Keep calling with
  `cursor` set to `next_cursor` until there is none; `matching` says how many calls
  the filters match.
- **Narrow first.** Use `agent_id`, `result`, `category`, `issue_id`, `version` and
  `period` so you read the calls that matter.
- **The analysis is yours.** Connexity filters on what it owns: issues, findings,
  versions, results, categories and the period. It does not search what was said or
  what a tool was called with. When a pattern is worth watching on every call, tell the
  person: it belongs in a check, and then `list_issues` answers it.
- **The same protections as one call:** callers as their last four digits, secrets in
  tool arguments and results masked.

For one call's timings and the events its findings point at, use `get_call`.

## One call

Call `get_call` with the call's `id` from `list_calls`. It answers the call's timeline in
order: each turn (agent or caller) with its text, and each tool call with its name,
status, duration, arguments and result (secret-looking values masked), and the n8n
workflow it ran. Its findings come worst first, each pointing at the entry it sits on
(`entry_index`) and saying whether a rule or a model found it. The caller shows as their
last four digits only; do not repeat their personal details unless the person asks.
