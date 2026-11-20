# Agent page issues and the daily score

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Agent page issues and the daily score"
  (10.1993). Builds on the score (10.19), the version filter (10.197), the chart
  (10.199) and the Overview's Score and Critical issues tiles (10.1992).
- **Design:** "Connexity Agent Profile" (design review 18, in `designs/screens/`): the
  Overview's Issues tile, the "Quality and latency" chart with its Score and Latency
  p50 panels, and the Issues tab. The Issues page design has no version filter; the
  Version picker (Decided below) is written up as a `designs/12-adjustments.md` item so
  the design does not fall behind.
- **MCP:** `get_agent` answers the daily score and the open issues count. `list_issues`
  already takes `version` (10.197). Rules, input descriptions and `contract.py` follow.

## Goal

The agent page design shows the agent's issues and its score over time; the build has
neither. 10.112 left them for later, 10.199 made the chart latency only, and 10.1992's
plan sent them to Issues work that had no row. After this merges, the agent page has an
Issues tab and an Issues tile, the chart shows the daily score above the daily p50, and
the Issues page takes a version, so every link from the agent page opens the same
issues it counts.

## Decisions

### In the roadmap row (Dmytro, 2026-11-20)

1. The daily score on the "Quality and latency" chart, next to the daily p50: the same
   formula as the Score (10.19), with each day's base (checked calls), following the
   version filter. `get_agent` answers it too.
2. The Issues tile on the Overview, with its open issues count.
3. The Issues list and an Issues tab on the agent page: the agent's issues, following
   the version filter.
4. A version filter on the Issues page, so the Overview's Critical issues and Issues
   tiles link there with the picked version, and the tab and the page show the same
   issues for the same agent and version.

### Decided while planning (Dmytro, 2026-11-20)

- **The list is on the Issues tab only,** as in the design: the Overview has the Issues
  tile, which opens the tab. No list under the chart.
- **The Issues page shows a Version picker beside the agent picker once an agent is
  picked,** listing that agent's versions with calls, as on the agent page. Picking
  another agent, or all agents, clears it.

### Proposed

- **The Issues tile opens the Issues tab;** the Critical issues tile keeps opening the
  Issues page, now with the picked version (10.1992's tile without a link goes).
- **The tab shows open issues only,** as the design does: grouped by category, worst
  first, each row with severity, title, calls affected and first seen, and opening the
  issue's page. It is the Issues page's list for that agent, so the numbers match.

## Changes

### The daily score

- **Each day's score:** the score formula over that day's checked calls of the agent,
  in the same days as the latency line. Findings of archived issues are hidden, as for
  the Score. With a version picked, only that version's calls.
- **Days without a checked call have no score;** the line steps over them, as the p50
  line does. Each day shows its base on hover: "Score 82 · 14 checked calls".
- **Before onboarding is complete there is no score,** as everywhere: the Score panel
  says "Ready when onboarding is complete".
- **The chart** becomes "Quality and latency": a Score panel (0, 50, 100) above the
  Latency p50 panel, one day axis and the version marks across both, as in the design.

### The Issues tile and tab

- **Issues tile:** the agent's open and reopened issues that showed in the period, as
  the Issues page's Open tile counts them for that agent; with a version, that
  version's.
- **Issues tab:** after Calls, its label carrying the open count, as in the design.
  Grouped by category with each group's count and critical count; "No open issues" when
  there are none.

### The Issues page version filter

- `GET /issues` takes `version`, as `list_issues` already does: only issues found on
  that agent version's calls.
- A Version picker beside the agent picker once an agent is picked (Decided above),
  listing that agent's versions with calls; the tiles follow it with the agent.

### API and MCP

- `GET /agents/{id}/page` answers `open_issues` and each latency day's `score` and
  `checked_calls`.
- `get_agent` answers the same; its rules say what the daily score and the open count
  are.

## Done when

- Route tests through the API (local database), with invented calls, findings and
  issues:
  - each day's score and checked calls equal the formula over that day's calls; a day
    without checked calls has none; none before onboarding;
  - with a version, the daily score, the Issues tile and the tab count only that
    version's calls;
  - the Issues tile and tab equal the Issues page's Open tile and list for that agent,
    with and without a version;
  - `GET /issues` with `version` lists only that version's issues;
  - `get_agent` answers the same; the contract test passes.
- For Dmytro to check on screen after merge: the chart's Score panel, the Issues tile
  and tab, and the Issues page's version filter.

## Out of scope

- Issues of other statuses (resolved, archived) on the agent's tab: the Issues page has
  them.
- A score goal line or warning colour on the chart: goals are parked.

## Risks

- A day's score over few checked calls swings; each day shows its base on hover.

## Outcome

### Deviations from the plan

- **The Critical issues tile reads "Critical",** as in the design, and always links to
  the Issues page, now with the picked version. 10.1992's tile without a link with a
  version picked goes.
- **The Issues tile opens the Issues tab** (Proposed, built as proposed).
- **One count for both tiles:** `critical_issues_by_agent` became
  `issue_counts_by_agent`, which answers each agent's open and critical issues in one
  pass; the Agents list and `list_agents` read its critical count as before.
- **Issue rows answer `first_seen_at`,** for the tab's First seen column. The Issues
  page answers `version` and, with an agent, its `versions` for the picker.
- **The Version picker is `designs/12-adjustments.md` item 35.**
- **The chart's caption** gives both bases: checked calls and replies.
- **Left as is (review):** a version mark on the first days of the period can put its
  label on the line of the Score panel's label.

### Check results

`make check`, run before the pull request: every step ok (plan, local database, pyright,
backend tests and coverage, MCP server tests, frontend lint and types, generated client
fresh) except backend lint, which flagged two unsorted import blocks. `ruff check
--fix` sorted them; backend lint, format and pyright then passed.

No separate play-through server: the route tests send the same requests through the API
(`TestClient` on the local database), with invented calls
(`test_agent_issues_daily_score.py`):
- each day's score and checked calls follow the formula over that day's calls (50 over
  2, then 100 over 1), other days have none, and `get_agent` answers the same days;
- no daily score before onboarding is complete;
- with a version picked, the daily score counts only that version's days;
- the Issues tile and critical count equal the Issues page's Open and Critical tiles for
  that agent, with and without a version; `GET /issues` with `version` lists only that
  version's issues, answers the agent's versions, and none for another workspace's
  agent; `get_agent` with `version` answers the same counts;
- the 10.1992, agent page, version filter, score, issues and dashboard tests pass.

For Dmytro to check on screen after merge:
- **Agent Overview:** five tiles (Score, Calls, Latency p50/p95, Critical, Issues). The
  "Quality and latency" chart has a Score panel (100, 50, 0) above Latency p50, version
  marks across both, each day's score and checked calls on hover. Before onboarding the
  Score panel reads "Ready when onboarding is complete".
- **Issues tab:** after Calls with the open count; issues grouped by category, with
  Severity, Issue, Calls affected and First seen; a row opens the issue; "No open
  issues" when there are none.
- **Issues page:** with an agent picked, a Version picker; the Critical tile on the
  agent page opens it on the picked version.

### Not done

- None.
