# Issues

An issue is one problem found on an agent's real calls: every call where Connexity's
checks found the same thing. Call `list_issues` with a `workspace_id` (and an
`agent_id` for one agent). Issues come worst first: open ones, then critical, then the
most calls affected.

Each issue has:

- **`severity`:** `critical` when its check fails the call, otherwise `warning`. Each
  check has a default; a person can change it per agent.
- **`found_by`:** `rule` when deterministic code over the call found it, the same
  answer every time; `model` when a classifier or judge did. Always tell the person
  which.
- **`category`:** one of the fixed categories (see `connexity://guides/categories`).
- **Its size:** `calls_affected` of `calls_total`. Say "in 11 of 78 calls".
- **`state`:** open, resolved, regressed (found again after it was resolved) or
  accepted.

## How to talk about them

- Lead with the critical ones and their size, grouped by category.
- Say how each was found.
- Do not quote callers or tool arguments unless the person asks about one call.
- Calls are checked within a minute of arriving, and every stored call is checked when a
  check is added or changes.
