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
- **Each call** has its time, agent, the caller's last four digits (never the number),
  duration, result and worst finding: the check's title, what broke (`key`), its
  category, severity and whether a rule or a model found it.

Results: **failed** when a finding fails the call, **degraded** when one only flags it,
**clean** when checks ran and found nothing, **unchecked** when none could run.
