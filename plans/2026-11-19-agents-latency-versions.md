# Agents list and agent Overview: p95 latency, versions, clean chart

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Agents list and agent Overview: p95
  latency, versions, clean chart" (10.199).
- **Design:** Claude Design review (18): "Connexity Agents", "Connexity Agent Profile"
  (Overview), "Connexity Home" (the Dashboard's latency tile) and "Connexity Agents and
  Overview". The Agents and Home screens are copied into `designs/screens/` with this
  PR, and the change is written up as `designs/12-adjustments.md` item 34. Where the
  review and the roadmap row differ, the review wins (the roadmap session, 2026-11-19).
- **MCP:** `list_agents` and `get_agent` answer latency as p50 and p95 and the agent's
  live version with since when. Their rules, descriptions and `contract.py` entries
  follow.

## Goal

The Dashboard already shows latency as percentiles over every reply. The Agents list
and the agent page still show an average of each call's median, and the list does not
say which version each agent runs. After this merges, the three screens measure latency
the same way, and the list names each agent's live version.

## Decisions

### Decided by Dmytro (2026-11-19, the roadmap row)

1. Latency is p95 with p50 on the Agents list and on the agent page, as on the
   Dashboard. The review shows it as "p50/p95", "1.6s/3.1s", with p50 large and p95 after
   it, and the Dashboard tile changes to the same order.
2. The Agents list shows each agent's current version, "v14", with "Since 6 Nov" on
   hover.
3. The agent page's chart marks only new versions, "v14": no marks for score drops or
   archived issues, legend "New version" only.

### Decided while planning (Dmytro, 2026-11-19)

- The agent page's chart follows the review: **one line of daily p50**, "Latency p50";
  p95 is in the tile above it.
- The Agents header's **"Retell · synced 5 minutes ago" goes**, as in the review.

### Proposed in the row, carried here

- No p95 line on the chart (Decided above); no latency goal line and no warning colour on latency: no latency goal exists, goals
  are parked, and nothing fake goes on screen.
- With a version picked (10.197), the chart keeps the whole period with that version's
  days highlighted. This is built; it stays.
- Per-agent p50 and p95 reuse the Dashboard's reply-gap percentiles
  (`crud/latency.py`).

### Already as decided

- The built chart has only version marks and the "New version" legend. The score-drop
  and archived-issue marks were never built.

## Changes

### One way to measure latency

- **p50 and p95 over every reply gap** of an agent's calls in the period: every time
  the agent answered the caller, as the Dashboard counts them. This replaces "the
  average of each call's median". It is computed for all agents in one pass over their
  turns, not one query per agent.
- **Daily p50** for the agent page's chart.
- **With a version picked** (10.197), only that version's calls count, as now.

### The Agents list

- **A Version column:** "v14", "Since 6 Nov" on hover (the first call on that version
  since the agent last ran another, as the agent page counts it). "—" for an agent with
  no call yet.
- **"Latency p50/p95":** "0.8s/1.7s", p95 muted; "—" without a reply in the period.
- **The header's "Retell · synced 5 minutes ago" goes.**

### The agent's Overview

- **The latency tile:** "Latency p50/p95", "1.6s/3.1s".
- **The chart:** one line of daily p50, "Latency p50", replacing the bars of daily
  averages. Version marks and the picked version's band stay. Its base stays: the
  period and how many replies it rests on.

### The Dashboard

- **The latency tile** flips to the review's order: "Latency p50/p95", p50 first.

### MCP

- `list_agents`: each agent's `latency_p50`, `latency_p95`, `live_version` and
  `live_since`. `latency_seconds` goes.
- `get_agent`: `latency_p50`, `latency_p95`, and per day for the chart. The latency rule
  says what is measured.

## Done when

- Route tests through the API (local database), with invented calls and turns:
  - the Agents list answers each agent's p50 and p95 over its reply gaps, its live
    version and since when;
  - the agent page answers p50 and p95, per day for the chart, and only the picked
    version's calls with a version;
  - `list_agents` and `get_agent` answer the same; the contract test passes.
- For Dmytro to check on screen after merge: the Agents list's Version and latency
  columns, the agent Overview's tile and chart, and the Dashboard tile's order.

## Out of scope

- Latency goals and their warning colour (parked).
- The Critical count on the agent page: the page has no Critical tile today.

## Risks

- p95 over few replies jumps around. Each number shows its base: how many replies it
  rests on.
- Reading every reply gap of every agent for the list is heavier than the old average.
  One pass over the period's turns, as the Dashboard does, keeps it to one query.

## Outcome

### Deviations from the plan

- **The chart steps over days without replies.** One line joins the days that had
  replies, with a dot on each, so calls a few days apart still draw a line and a single
  day still shows. The first version broke the line at every empty day, and sparse data
  drew nothing (found in review).
- **The old measure is deleted:** `call_latency`, `call_latencies` and
  `agent_latencies` go, and so does the list's `synced_at` with its query, since only
  the caption read it.
- **`live_since` moved** into the agents list service, which the agent page already
  imports, and is called once per agent on the list. That is two queries per agent;
  the list is one workspace's agents and MCP pages them by 25 (review, left as is).
- **API names:** the agent page answers `latency_p50`, `latency_p95` and
  `latency_replies`, and each day `p50` and `replies`. `latency_seconds` and
  `latency_calls` go.

### Check results

`make check`, run before the pull request: every step ok (plan, local database, backend
lint and format, pyright, backend tests and coverage, MCP server tests, frontend lint and
types, generated client fresh).

No separate play-through server: the route tests send the same requests through the API
(`TestClient` on the local database), with invented calls and turns:
- p50 and p95 by nearest rank over reply gaps;
- the agent page: three replies a call, at 1 s and 2 s, give 1.0s/2.0s over 6 replies,
  with each day's p50 and the peak;
- the Agents list gives each agent's p50 and p95 (1.0s/3.0s), its live version and
  since when, and none for an agent without calls;
- `get_agent` and `list_agents` answer the same, with the new latency rule;
- the version filter tests from 10.197 pass on the new measure.

For Dmytro to check on screen after merge:
- **Agents list:** the Version column ("v14", "Since 6 Nov" on hover), "Latency p50/p95"
  ("0.8s/1.7s"), and no "synced" caption.
- **Agent Overview:** the "Latency p50/p95" tile, the "Latency p50" chart as a line with
  dots and version marks, and the picked version's shaded days.
- **Dashboard:** the latency tile reads p50 first.

### Not done

- None.
