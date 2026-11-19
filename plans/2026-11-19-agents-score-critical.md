# Score and critical issues on the Agents list and agent Overview

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Score and critical issues on the Agents list
  and agent Overview" (10.1992). Builds on the score (10.19), the version filter (10.197)
  and the Agents list's latency and versions (10.199).
- **Design:** "Connexity Agents" and "Connexity Agent Profile" (design review 18, in
  `designs/screens/`), "Connexity Agents and Overview", and `designs/12-adjustments.md`
  items 1 and 11. No new design adjustment: the screens already show both.
- **MCP:** `list_agents` and `get_agent` already answer the score; they gain the
  critical issues count. Their rules and `contract.py` entries follow.

## Goal

The score is built (10.19, per agent and per workspace) but shows only on the
Dashboard. The Agents list and the agent page leave it out, with comments saying score
and critical issues "wait for their features". After this merges, both screens show
each agent's score with its change, and its critical issues, with the same numbers as
the Dashboard and the assistant's tools for the same agent and period.

## Decisions

### In the roadmap row (Dmytro, 2026-11-19)

- The Agents list gets the design's Score and Critical issues columns. The agent
  Overview shows the agent's score with its change over the period, and its critical
  issues count, as in the design.
- The same numbers as the Dashboard and as `get_agent` and `list_agents` for the same
  agent and period. They follow the version filter (10.197) where the agent page has
  one. They show only once onboarding is complete, as on the Dashboard.
- The two "wait for their features" comments go.

### Decided while planning (Dmytro, 2026-11-19)

- The Agents list is ordered **lowest score first**, as in the design; agents without a
  score come after, most calls first.
- The critical issues count **links to the Issues page** filtered to that agent's
  critical issues, on the list and on the Overview tile.

## Changes

### What the numbers are

- **Score:** the agent's score for the period and its change against the period before,
  from the same `score` function the Dashboard and `get_agent` use. Before onboarding
  is complete, or without a checked call, there is no score: the list shows "—", and the
  tile says why, as on the Dashboard ("Ready when onboarding is complete", "No checked
  calls yet").
- **Critical issues:** the agent's open or reopened issues of critical severity that
  showed in the period, as the Issues page's Critical tile counts them for that agent.
  With a version picked, only issues found on that version's calls, as `list_issues`
  with `version` counts them. Counted for every agent of the list in one pass.

### The Agents list

- **Score** and **Critical issues** columns, as in the design: the score in bold, the
  critical count in red with its icon when above zero, "0" muted otherwise.
- **The order:** lowest score first; agents without a score after, most calls first.
- The critical count links to the Issues page filtered to that agent and critical
  severity. A row is already a link to the agent, so the count is its own link beside
  it, not one inside the other.

### The agent Overview

- **Tiles:** Score (with its change, "+4" or "−3"), Calls, Latency p50/p95, Critical
  issues: four tiles in one row, as in the design without its Issues tile. The Critical
  issues tile links to the Issues page as the list's count does.
- With a version picked, the score and critical count are that version's.

### API and MCP

- `GET /agents/list` answers each agent's `score`, `score_change` and
  `critical_issues`; `GET /agents/{id}/page` answers `score` (with its change and why
  there is none) and `critical_issues`.
- `list_agents` and `get_agent` answer `critical_issues`, and their rule says what it
  counts.

## Done when

- Route tests through the API (local database), with invented calls, findings and
  issues:
  - the Agents list and the agent page answer each agent's score, change and critical
    issues, equal to `get_agent`, `list_agents` and the Issues page's Critical tile for
    that agent and period;
  - before onboarding is complete there is no score, with why;
  - with a version picked, the agent page's score and critical issues count only that
    version's calls.
- The contract test passes with the new field described.
- For Dmytro to check on screen after merge: the Agents list's Score and Critical issues
  columns and their order, and the agent Overview's Score and Critical issues tiles.

## Out of scope

- The design's other Overview parts: the Issues tile with its open count, the score line
  on the "Quality and latency" chart, and the Issues list under it. They belong to the
  agent page's Issues work.
- An Issues tab on the agent page.

## Risks

- The score swings on few checked calls; each score shows its base where there is room
  (the tile's hover), as on the Dashboard.

## Outcome

### Deviations from the plan

- **With a version picked, the Critical issues tile is not a link.** It reads
  "Critical issues on version 87" and counts only that version's issues, while the
  Issues page has no version filter and would show every version's. Without a version
  it links as planned (found in review).
- **The list's critical count is laid over the row's link**, not nested in it: the
  agent's name is the row's link, stretched over the row, and the count is its own link
  above it.
- **The score is computed twice for `get_agent`:** the agent page computes it without
  what moves it, and `get_agent` again with it. Left as is (review); a few queries per
  call.
- **`contract.py`:** the `list_agents` and `get_agent` summaries name critical issues.

### Check results

`make check`, run before the pull request: every step ok (plan, local database, backend
lint and format, pyright, backend tests and coverage, MCP server tests, frontend lint and
types, generated client fresh).

No separate play-through server: the route tests send the same requests through the API
(`TestClient` on the local database), with invented calls, findings and issues
(`test_agents_score_critical.py`):
- the Agents list orders lowest score first, then agents without a score; each row's
  score, change and critical issues equal `get_agent`, `list_agents` and the Issues
  page's Critical tile for that agent;
- before onboarding is complete there is no score, with why, and the critical count
  still shows;
- with a version picked, the agent page's score and critical issues count only that
  version's calls;
- the earlier Agents list, agent page, version filter and score tests pass unchanged.

For Dmytro to check on screen after merge:
- **Agents list:** Score and Critical issues columns, lowest score first; the critical
  count in red with its icon above zero, and a click on it opens Issues filtered to that
  agent's critical issues; a click elsewhere on the row opens the agent.
- **Agent Overview:** four tiles: Score with its change (or "Ready when onboarding is
  complete"), Calls, Latency p50/p95, Critical issues opening Issues; with a version
  picked, that version's numbers.

### Not done

- None.
