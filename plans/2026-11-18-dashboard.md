# Dashboard

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Dashboard" (10.191). Builds on the score
  (10.19, Connexity-AI/connexity#232); starts once it merges.
- **Design:** `Connexity Home.dc.html` from the design review delivered 2026-11-18 (zip
  15), with `Connexity Home v1.dc.html` keeping the previous version; both added to
  `designs/screens/`, with the changed `Connexity.dc.html`.
- **MCP:** a new tool, `get_dashboard`, answering the same picture; its contract-page
  entry and input descriptions (CLAUDE.md rule 10).

## Goal

A founder opens the Dashboard and sees in seconds where they are with their voice
agents: the score, failed and degraded calls with their share, latency, calls per day,
and how each area of the agents' work is doing. The assistant gets the same picture
through `get_dashboard`.

## Decisions

- **Accept, build** (Dmytro, 2026-11-18).
- **The Dashboard tells a founder "where am I"; never the word "audit"** (Dmytro,
  2026-11-18, the row).
- **Page bar** with the scope (agents, calls), an agent picker and the period picker.
- **While onboarding runs,** a thin status strip (Scan, Spec, Answers N of M, Complete;
  areas checked), gone once complete.
- **Tiles:** Failed and Degraded (from call results, with their share), Latency p95 with
  p50 beside it (percentiles are new), and the Score card with its change; no
  milestones and no tasks under it.
- **Calls per day,** stacked failed and degraded, with version marks.
- **Areas:** one row per fixed category, status by rule: Critical with failed calls,
  Warning with only degraded, Healthy when checked and clean, Not checked yet with what
  it waits for; never green before checked.
- **Exposure** (money, safety, compliance) only once it works: not in this build.
- **No agents list, no weekly trend, no tasks.**
- **Ships with an MCP tool answering the same picture.**
- **All areas are shown (the 14 fixed categories; 15 in the question was a miscount);** one no check covers reads "Not checked yet · No check covers
  this area yet" and sits at the bottom (Dmytro, 2026-11-18, question 1).
- **Latency p95 and p50 are taken over every reply gap in the period,** every time the
  agent answered the caller (Dmytro, 2026-11-18, question 2).

## What exists

- **Calls by result** per period and agent (the Calls page's tiles) and **the score**
  (10.19).
- **Latency:** each call's latency is the median of its reply gaps; an agent's latency
  is the average over its calls (`crud/latency.py`). No percentiles.
- **Version starts** per agent (`agent_version_starts`), used on the agent and issue
  pages.
- **Categories:** 14 fixed ones; checks belong to one each. Today only two have checks:
  Booking, and Tools and integrations.
- **Onboarding:** the ordered list (10.18) and Readiness; clarifications with their
  answered and open counts.
- **The web app** lands on Work; `/` redirects there. There is no Dashboard page and no
  sidebar entry for it.

## Changes

### What the Dashboard counts (backend, `services/dashboard.py`)

For the workspace or one agent, for 7, 30 (default) or 90 days:

- **Scope:** agents counted and calls in the period.
- **Tiles:**
  - Failed and Degraded calls, each with its share of the period's calls;
  - Latency p95 and p50 over every reply gap in the period, with the number of
    answers they rest on;
  - the Score with its change (10.19), or "Ready when onboarding is complete".
- **Calls per day:** for each day, calls, failed and degraded, and the version marks of
  the agents in scope ("Car service booking moved to v14 on Nov 4").
- **Areas,** one row per fixed category, all 14:
  - **Critical** when a check of that area failed calls in the period, **Warning** when
    it only degraded them, **Healthy** when a check of that area ran on the period's
    calls and found nothing;
  - **Not checked yet** otherwise, with what it waits for: "No check covers this area
    yet" when no check belongs to it, "No calls checked yet" when one does but has not
    run in the period;
  - for Critical and Warning: the share of calls and the area's top issue (most calls),
    linking to Issues filtered by that category;
  - order: Critical, Warning, Healthy, Not checked yet; then by calls affected.
- **Onboarding strip,** while onboarding is not complete: Scan, Spec, Answers N of M,
  Complete, each done or not, read from the onboarding list and the clarifications;
  "N of 14 areas checked".

### The page

- **`/dashboard`,** from the design: page bar, strip, tiles, chart, areas, dark and
  light, narrow.
- **The sidebar** gains Dashboard after Work, as decided (2026-11-16). Work stays the
  landing page.
- **Areas link** to Issues with the category filter; a Not checked yet row does not
  link.
- **No sample data:** everything on the page comes from the backend (rule 14).

### MCP

- **`get_dashboard(workspace_id, agent_id?, period?)`:** the same picture as data, with
  rules (how each number is counted, the score's formula, what each area status means)
  and next steps (the worst area's top issue with `get_issue`; while onboarding runs,
  `get_next_task`).
- **Contract page:** its entry (group Calls and issues, Reads) and every input described.

### Docs

- `docs-internal/metrics.md`: latency percentiles.
- `docs-internal/work.md` or a short Dashboard section in the design notes: what each
  part counts.

## Done when

- Through the API on the local database, with invented calls: the tiles, the per-day
  counts and marks, each area status (Critical, Warning, Healthy, Not checked yet), the
  onboarding strip before and after onboarding, for all agents and for one.
- `get_dashboard` answers the same.
- `make check` passes.
- **For Dmytro on screen:** `/dashboard` for all agents and one, the three periods, during
  onboarding and after; dark, light, narrow.

## Out of scope

- Exposure (money, safety, compliance).
- Milestones, tasks, an agents list, a weekly trend.
- Changing the landing page.

## Risks

- **Most areas show "Not checked yet"** until more checks and spec rules exist (12 of 14
  today). Honest, but the page looks thin on a first look.
- **Percentiles over few calls** are noisy; the tile shows the calls they rest on.

## Questions

None left: both were answered (see Decisions).

## Outcome

### Deviations from the plan

- **14 areas, not 15:** every fixed category is one row; the question said 15 by a
  miscount (confirmed by Dmytro with "Accept, build").
- **The onboarding strip's "complete"** is scan, specs and answers all done (Readiness's
  first scan, no agent waiting for a spec, no open clarification). The score's gate is
  Readiness's own onboarding check; the two can differ for a moment, so the strip can
  show while the score is already shown, or the other way round.
- **Latency is over every agent of the workspace** whose calls count, not only linked
  ones, so it rests on the same calls as the results and the score (`/code-review`).
- **Area rows link to Issues with the same period and agent**, not the category alone
  (`/code-review`).
- **A stale `agent` in the address** (another workspace's, or not an id) falls back to
  all agents instead of an error.

### Check results

`make check`: every step ok (backend lint, format and types; all backend tests; MCP
server tests; frontend lint and types; generated client fresh) except "plan complete",
which was this Outcome. `pnpm --filter web build`: ok. No separate play-through server:
the route tests send the same requests through the API.

**Tests** (`test_dashboard.py`, 4, local database, invented calls): nearest-rank
percentiles in seconds; for two agents and four calls, one failed: 4 calls, failed 1
(25%), degraded 0, score 75, 31 days summing to the calls, 14 areas with Booking
critical and its top issue, Tools and integrations healthy, Greeting not checked with
"No check covers this area yet", critical first and not checked last, and a `get_issue`
next step; for one agent: 1 call, Booking healthy, score 100; the strip's four steps
and 14 areas while onboarding runs, with no score; 404 for another workspace's agent.
MCP server tests: 53, with `get_dashboard` registered and described on `/mcp-docs`.

**`/code-review` (high), 4 findings, all fixed:** area link dropped the period and
agent; a stale agent broke the page; latency over linked agents only; days not forced
to UTC.

### For Dmytro on screen

- **Sidebar:** Dashboard sits after Work.
- **/dashboard** (30 days, all agents): Score, Failed, Degraded and Latency tiles, each
  with its base; calls per day with failed and degraded stacked, version marks and date
  ticks; 14 area rows, critical and warning first, each linking to Issues of that area
  over the same period and agent; not-checked rows say what they wait for.
- **Pickers:** 7 / 30 / 90 days and one agent change every number and the chart.
- **While onboarding runs:** the strip (Scan, Spec, Answers N of M, Complete) on top and
  no score; gone once all three are done.

### Not done

- Nothing from the plan.
