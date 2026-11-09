# The web app is a dashboard for a quick glance

- **Owner:** Dmytro
- **Slice:** none (design direction; the roadmap is paused until the design work is done)
- **Design:** [Connexity Design System](https://claude.ai/artifact/QcryjvPtMFxDiL2NcTNEv6),
  version 7 (`1794260848-fa4d`), whose rules were rewritten for dashboards at Dmytro's
  request ("feel free to update rules"). The first home draft is the
  [Connexity home](https://claude.ai/artifact/8wvbhxsAMEoxqSEPJjjMpc) canvas, not yet
  approved. No code changes.
- **MCP:** None needed: documents only. Nothing a user can do or see in the running
  product changes. The rule that every feature ships with MCP tools stays.

## Goal

The repo docs describe the web app the way Dmytro now sees it: a dashboard that gives a
person a quick glance at the whole fleet. Today they say the opposite: the app is
"reports and things to do", and `frontend/CLAUDE.md` lists "dashboards of metrics"
under "Do not add". A session that reads them would build the report Dmytro rejected.

## Changes

Documents only:

- **`CLAUDE.md`**: the sentence on the web app says it is a dashboard for a quick
  glance at the fleet, plus a single call, built from the design system.
- **`frontend/CLAUDE.md`**, "What the UI is for": the same, with the rules that shape
  every screen: every number shows its base (agents, calls, period), findings and
  progress come before anything that asks the person, and the sidebar is Home, Agents,
  Roadmap, Issues and Settings. "Do not add" drops "dashboards of metrics" and keeps
  trace explorers, filters other than the period, and drill-downs below a single call.
- **Lifecycle guide, section 6**, "What the web app is for": rewritten to match, with
  the new decision quoted. The 2026-11-09 morning decision ("reports and things to
  do") is marked as superseded there, not deleted, because the decision log keeps it.
- **`REBUILD.md`**:
  - a decision-log row for the dashboard direction and the sidebar
  - the "Kept after checking the code" row for the create-agent and Integrations forms
    cites the new wording
  - parked slice 1.7 opens a call from the dashboard, an issue or a to-do, not "from a
    report"

Left as it is: `checks-and-incidents.md` says there is "no outcome dashboard". That is
about business outcomes (conversion, revenue), which Connexity never measures, and still
holds.

## Decisions

Made by Dmytro on 2026-11-09:

- The home page is a dashboard, not a report ("The home page should look more like
  dashboard and less then cheap claude report").
- Connexity's value next to the assistant is the quick glance ("the only value of the
  system vs ai assistant is to have a quick glance of whats going on and thats what
  dashboards are for").
- Numbers show their base: agents and calls, or they are confusing ("it should show the
  number of agents and calls otherwise its very confusing numbers").
- The sidebar is Home, Agents, Roadmap, Issues, Settings ("It will have Home, Agents,
  Roadmap, Issues, Settings").
- A screen gives before it asks ("Immediate effect should be give something not ask").
  It shows issues found, how many are critical and how many clarifications are needed,
  as numbers, then a score and a path to progress.
- There is a score for the fleet and for each agent ("both"). How it is made is not
  designed yet.
- Clarifications are answered in the app and through the assistant, in small batches,
  not all at once ("both assistant and app… make it in chucnks").
- Nothing is reserved for a person: everything can be done through MCP ("there is
  nothing only person can do everything should be possible to do with mcp").
- The design system's rules may change to match ("feel free to update rules").

Proposed by Claude, not separately confirmed:

- The period is the only filter on a screen.
- The single call stays the deepest view; nothing below it on screen.
- What Settings holds is Open. The Proposed note that forms stay only for signing in
  and the person's own account stays as it is until Settings is designed.

## Done when

- No document outside `plans/` and the decision log says the web app is only reports
  and things to do, or forbids dashboards.
- The decisions above are in `REBUILD.md`'s decision log in Dmytro's words.
- `make check` passes.

## Out of scope

- Any screen design or frontend code.
- The design system's component set (tiles and charts are described in its rules, but
  not built as components yet).
- Rewriting the roadmap.

## Risks

- **"Dashboard" can pull toward an observability tool**, the thing Dmytro ruled out in
  the morning. The docs keep the limits explicit: no trace explorers, no query
  builders, one filter, nothing deeper than a single call.
- **The score is named before it is designed.** The docs say it exists and leave its
  making Open, so no session invents a formula.

## Outcome

### Deviations from the plan

- **`frontend/CLAUDE.md` marks only the new limits as Proposed.** "No trace explorers
  and nothing below a single call" stays Decided (from the morning); "no query builders
  and no filter other than the period" is marked Proposed.
- **Slice 1.7's "Done when" now starts from an issue or a to-do**, not a report line,
  matching its new opening line.

Otherwise as planned.

### Check results

`make check` on this branch: every step passed in one run.

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Start local database | ok | 1s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 8s |
| Backend tests and coverage | ok | 74s |
| MCP server tests | ok | 3s |
| Frontend lint | ok | 1s |
| Frontend types | ok | 2s |
| Generated client is fresh | ok | 8s |

A search of `CLAUDE.md`, `frontend/CLAUDE.md`, `docs-internal/` and `REBUILD.md` for
"reports and things to do", "dashboards of metrics" and "from a report" finds only the
decision-log history and the lifecycle sentence that says the old wording was replaced.

`/code-review` was not run: no code changed, only documents and this plan.

For Dmytro to check: nothing on screen changes in the app.

### Not done

- What Settings holds is still Open; the Proposed note on forms is unchanged.
- The home canvas is a draft and not approved, so no design version is cited for it.
