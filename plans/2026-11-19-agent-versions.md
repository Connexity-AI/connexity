# Agent page: versions on calls, issues and spec

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Agent page: versions on calls, issues and
  spec" (10.197). Builds on 10.196 (PR #241); this branch starts once that merges.
- **Design:** Claude Design, "Connexity Agent Profile" (version filter beside the period,
  the Overview's numbers and charts for one version, Calls with a Version column, "Spec 5
  · written for version 88"), "Connexity Calls" (the Version column inside the agent
  page) and "Connexity Agents and Overview" (Overview with a version picked), from design
  reviews (17) and (18). Written up as `designs/12-adjustments.md` item 33. The Overview's
  latency as p50/p95, the chart's removed markers and the "Agents and Overview" screen
  are also in (18); they belong to roadmap row 10.199 (confirmed by the roadmap session,
  2026-11-19), so they are not built here.
- **MCP:** `list_calls`, `list_issues` and `get_agent` take a `version` input, and
  answers carry each call's version. `get_agent` lists the agent's versions. Their
  `contract.py` entries and input descriptions follow.

## Goal

Dmytro asked on 2026-11-19 to see an agent's version on its calls. Today the agent page
mixes bases: Overview and Calls follow the period, Tests follows the agent version, and
the spec has its own number (spec 5 while the agent is on version 88). After this merges
the person can pick one version beside the period and see that version's numbers and
calls, so "is 88 better than 87" is one pick. The spec says which agent version it was
written for.

## Decisions

### Decided by Dmytro (2026-11-19, the roadmap row)

1. "Period + version filter": keep the period picker and add the version as a filter.
   The Calls tab gets a Version column and the filter; Issues and Overview can be
   filtered by version too. Numbers stay comparable with the Dashboard.
2. "Yes, show both": a spec version says which agent version it was written for, "Spec 5
   · written for version 88".

### Decided while planning (Dmytro, 2026-11-19)

- The issues version filter is **MCP only for now** (`list_issues` with `version`); the
  agent page's Issues tab gets it when that tab is built.
- **Spec and Tests both follow the filter.** Tests shows the picked version's verdict
  and runs. Spec shows the spec written for the picked version.
- The filter lists **every version that has a call**, newest first, the live one marked.

### Already there

- Every call stores `agent_version` (all 90 production calls have it), and a spec stores
  the `agent_version` it was written for.

## Changes

### The version filter

- **Beside the period picker** on the agent page: "All versions" by default, or
  "Version 88 · live". The list holds the agent's versions that have calls, newest
  first, the live one marked (Proposed in the row).
- **With a version picked, the period still applies:** the numbers are that version's
  calls within the period. The pick lives in the URL (`?version=87`), so it survives a
  reload and can be shared.
- **Every tab follows it:** Overview, Calls, Spec and Tests.

### Overview

- With a version picked: the Calls, latency and score tiles count only that version's
  calls in the period. The latency chart dims the other days and shades the picked
  version's days (the design's band). Version marks stay.
- `GET /agents/{id}/page` takes `version` and answers the agent's versions (number,
  calls, live).

### Calls tab

- A **Version** column on the agent page's Calls tab only (the Calls page keeps its Agent
  column), and the filter applied to the list and its tiles.
- `GET /agents/{id}/calls` and the call list's filters take `version`; each call carries
  `agent_version`.

### Spec tab

- The title reads "Spec 5 · written for version 88" (today "Version 5 · agent version
  88"). The versions picker keeps its "Compare with version N", where N is the spec's
  number.
- **With a version picked,** the tab shows the newest spec written for that version or
  an earlier one (Proposed: a spec stays in force until the next is written). If none,
  the empty state reads "No spec was written for version 87 or earlier." Rule marks come
  from that version's latest full run.
- `GET /agents/{id}/spec` takes `for_version`.

### Tests tab

- With a version picked, the tab shows that version's verdict, tiles and runs (the
  results already read one version; `GET /agents/{id}/tests` takes `version`). Earlier
  versions' runs stay behind their link.

### Issues

- `list_issues` takes `version`: the issues found on that version's calls in the period,
  each counting only those calls. No filter on a screen yet.

### MCP

- `list_calls(version)`, `list_issues(version)`, `get_agent(version)`: each answers for
  that version's calls. Answers say which version they cover. `get_agent` lists the
  versions with their calls, newest first, the live one marked, and a next step to
  compare two versions by calling it with each.
- Each call in `list_calls` and `get_call` carries its version (`agent_version`, already
  on `get_call`).

## Done when

- Route tests through the API (local database), with invented calls on versions 87 and
  88:
  - `GET /agents/{id}/page?version=87` counts only version 87's calls and lists both
    versions, 88 marked live;
  - `GET /agents/{id}/calls?version=87` lists only those calls, each with its version;
  - `GET /agents/{id}/spec?for_version=87` shows the spec in force for 87, or none;
    `GET /agents/{id}/tests?version=87` shows 87's verdict and runs;
  - `list_calls`, `list_issues` and `get_agent` with `version` answer for that version;
    the contract test passes with the new inputs described.
- For Dmytro to check on screen: the filter on the agent page, the Overview with a
  version picked (tiles and the shaded band), the Calls tab's Version column and filter,
  the Spec tab for a picked version (and its empty state), the Tests tab for a picked
  version, and the Spec title.

## Out of scope

- The agent page's Issues tab, score chart and critical issues (their own features).
- Latency as p50/p95, the chart's removed markers, the Agents list's current version
  and the Dashboard tile's format from design review (18): roadmap 10.199.
- Comparing two versions side by side.

## Risks

- A version picked with no calls in the period shows zeros; the empty state must say
  "No calls on version 87 in the last 30 days", not look broken.
- The score for one version uses the same formula over fewer calls; with few calls it
  swings. It shows its base ("over 12 checked calls"), as every number does.

## Outcome

### Deviations from the plan

- **The agent page's Calls tab reads `GET /calls`** (the workspace calls list with
  `agent_id`), not `GET /agents/{id}/calls`, which serves 1.x. `version` was added there,
  and every call in that list now carries `agent_version`.
- **The Overview has no score tile today** (the score is MCP only), so the version
  filters Calls, latency, the latency chart and the systems on screen. `get_agent` with
  `version` also gives that version's score.
- **The spec in force** is the spec written for the highest agent version at or below
  the asked one, the newest such spec first. Non-numeric versions match by equality
  only.
- **A version from a link that has no calls** still shows as picked in the filter, with
  zeros and the "No calls on version N" note.
- **With a version picked,** the Tests tab says "N runs on other versions", because
  newer versions' runs are among them.
- **The filter's clear item** reads "All versions" (`Picker` takes a `clearLabel`).
- `list_calls` loses its separate version lookup for issue calls, since every call now
  carries its version.

### Check results

`make check`, run before the pull request: every step ok (plan, local database, backend
lint and format, pyright, backend tests and coverage, MCP server tests, frontend lint and
types, generated client fresh). One existing test changed its expectation: a call
listed without an issue now carries its agent version (`test_mcp_fix_loop.py`).

No separate play-through server: the route tests send the same requests through the API
(`TestClient` on the local database), with invented calls on versions 87 and 88:
- `GET /agents/{id}/page` lists both versions, 88 live. With `version=87` it counts
  only 87's two calls and names the days it ran;
- `GET /calls` with `agent_id` and `version` lists only that version's calls, each with
  its version;
- `get_agent` with `version` answers for it, and without one suggests comparing
  versions; `list_calls` with `version` lists only its calls; `list_issues` with
  `version=87` finds the missing-zip issue on 1 of 87's 2 calls, and none on 88;
- `GET /agents/{id}/spec` with `for_version` gives the spec written for 87, keeps the
  latest for a later version, and has none before the first spec;
- `GET /agents/{id}/tests?version=87` answers 87, not verified;
- the MCP adapter sends `version` on `get_agent`, `list_calls` and `list_issues`.

For Dmytro to check on screen (agent page):
- **The filter beside the period:** "All versions", each version with "· live" on the
  live one.
- **Overview with a version picked:** "Calls on version 87", latency for it, the shaded
  days on the chart, and the note when it had no calls in the period.
- **Calls tab:** a Version column; with a version picked, only its calls.
- **Spec tab:** "Spec 5 · written for version 88". With a version picked, the spec in
  force for it, or "No spec was written for version 87 or earlier".
- **Tests tab with a version picked:** that version's verdict and runs.

### Not done

- No test for the spec-in-force order when an older version's spec is written after a
  newer one's. The order is written but no test exercises it.
