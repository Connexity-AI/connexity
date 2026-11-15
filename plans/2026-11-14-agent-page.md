# Agent page basics: Overview and Calls

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Agent page basics: Overview and Calls"
  (10.112).
- **Design:** `designs/screens/Connexity Agent Profile.dc.html` (the page bar, tabs,
  Overview and Calls), `designs/screens/Connexity Agents.dc.html` (the Latency column
  and clickable rows). Prompts `designs/02-agents.md` and `04-agent-profile-tabs.md`
  (Overview part). The screens win where they differ, minus what the roadmap leaves out.
- **MCP:** adds `get_agent(workspace_id, agent_id)`, the same facts as Overview.
  `list_agents` gains latency.

## Goal

A person clicks an agent on the Agents page and sees, at a glance, how it is doing and
what it is made of:

- its calls and latency in the period;
- the platform, type, live version, model and the systems it uses;
- latency over time, with a mark at each new version;
- its calls, as on the Calls page.

From the roadmap: "Agents rows become clickable and gain an average latency column. The
agent page has the Overview and Calls tabs (Spec joins with the spec feature). Overview:
Calls and Latency tiles, the read-only details card (platform, type, live version,
model, systems it uses), latency over time with version marks. No score, issues or
quality chart yet. Calls tab: the Calls list filtered to the agent."

## What exists today

- **The Agents page** (#201): name, platform and type, calls, "No spec". Rows open
  nothing.
- **Each call's trace** has every turn with its speaker and start and end times
  (`call_event`). So the time between the caller stopping and the agent starting to
  answer can be measured for any provider.
- **The catalogue** knows each agent version, what it links to (its prompt or flow and
  its model), and every n8n workflow version its tool calls ran (kind `skill`).
- **The Calls page** filters by agent and is built to be reused.
- **Each call records its agent version,** so the "live version" and when it started
  can be read from calls.

## Changes

### Latency (question 1)

**A call's latency** is the median of its reply gaps. A reply gap is the time from the
end of a caller's turn to the start of the agent's next turn.

- It is measured from the trace, so it works for every provider, not only Retell.
- An agent reply that starts while the caller is still speaking is not a gap. This
  follows the finding in `REBUILD.md` that callers say "yeah" over the agent.
- **An agent's latency for a period** is the average of its calls' latencies, shown as
  "1.2 s".
- **It is worked out when it is asked for,** from the stored events. No new table,
  unless the play-through shows it is slow (see Risks).

### Backend

- **`GET /agents/list`** (the Agents page) gains each agent's latency in the period.
- **`GET /agents/{agent_id}/page?period=`** (one call answers the Overview):
  - **Page bar:** name, platform, type, and the live version with since when, for the
    caption "Retell · Conversational flow · version 14, live since 6 Nov". "Live" means
    the version of its most recent call, and "since" the first call on it.
  - **Tiles:** Calls and Latency in the period.
  - **Details:**
    - platform;
    - type;
    - live version and since when;
    - the model of the live version from the catalogue (its name, for example
      "gpt-4.1");
    - **systems:** the n8n workflows its tool calls ran in the period, each with its
      latest version ("quote-lookup v7"). Failing marks wait for their feature
      (question 2).
  - **Latency over time:** the average per day for the period, with a mark on the day
    of each new agent version ("Version 9").
  - **Spec state,** for the "No spec" label next to the name.
- **`get_agent` (MCP):** the same answer for the assistant, plus how latency is
  measured, so it can explain the number.
- **`list_agents`** gains `latency_seconds`.

### Frontend

- **Agents page:**
  - rows become links to `/agents/{id}`, with the hover;
  - a **Latency** column between Agent and Calls;
  - the goal colour waits, because there is no goal yet.
- **The agent page,** as the export shows it, without what the roadmap leaves out
  (rule 14):
  - **the page bar:** the name, "No spec" when it has none, the caption and the period
    picker;
  - **two tabs: Overview and Calls,** with the Calls count on the tab. Issues, Spec and
    Tests are left out;
  - **Overview:**
    - the Calls and Latency tiles, with no Score, Critical or Issues;
    - the Details card;
    - **"Latency"** over time: the design's "Quality and latency" chart with only the
      latency half, no goal line, and only "New version" in the legend;
  - **Calls:** the Calls page's list, filtered to this agent, with its search, filters
    and period. The Agent filter and the Agent column are hidden, since the agent is
    fixed.
- **The sidebar** keeps Agents selected on the agent page.

### Docs

- `docs-internal/mcp-architecture.md`: `get_agent`, and `list_agents` gaining latency.
- The getting-started guide mentions `get_agent`.
- **A short "how latency is measured" note** in `docs-internal/` (new,
  `metrics.md`), since it will be reused by the score and alerts.

## Decisions

Decided by Dmytro:

- **The roadmap's scope:** Overview and Calls tabs; no score, issues or quality chart
  (roadmap entry).
- **The Agents and agent pages come before Clarifications** in the Demo milestone
  (2026-11-14, through the roadmap).
- **Small charts always show their time scale** (2026-11-12): start and end labels,
  the peak with its unit.

Proposed by Claude:

- **Latency is measured from the trace,** as a basic first measure to improve later
  (Dmytro, 2026-11-14).
- **"Live version"** is the version of the most recent call, and "since" the first call
  on it.
- **One route answers the whole Overview,** like the issue page.
- **The Calls tab reuses the Calls page,** with the agent fixed.

## Answered questions

Dmytro, 2026-11-14: "do basic latency and we will work on it in future to make it more
useful / agree with rest".

1. **Latency** is the basic measure: from the trace, the median reply gap per call,
   averaged across calls. It is to be made more useful later.
2. **No "failing" mark** on systems yet.
3. **No latency goal** (colour or line) until a goal can be set.

## Done when

- `make check` passes. Backend tests cover:
  - a call's latency from turns: overlaps ignored, no gap when the agent never
    answers;
  - an agent's latency per period;
  - the Agents list's latency;
  - the agent page: caption, tiles, details (model and systems), latency per day with
    version marks, and the spec state;
  - another workspace and an unknown agent;
  - `get_agent` and `list_agents` latency.
- Played through on a running backend through the API and MCP.
- **For Dmytro to check on screen** (after merge, the demo workspace):
  - an Agents row opens the agent;
  - the Latency column;
  - the page bar caption;
  - the two tabs;
  - the tiles;
  - the Details card;
  - the latency chart with version marks and its time scale;
  - the Calls tab filtered to the agent;
  - dark and light.

## Out of scope

- **Score, critical issues, issues and the quality chart** (later).
- **The Spec, Issues and Tests tabs** (after the demo, and later).
- **Latency goals and "failing" systems** (questions 2 and 3).
- **Storing latency per call:** only if it is needed for speed.

## Risks

- **Working latency out on request** reads every turn of every call in the period. That
  is fine at demo size, but slow at thousands of calls. If the play-through shows it,
  latency is stored on each call when it is checked, which is a small follow-up.
- **Calls without turn timings** have no latency and are left out of the average. The
  answer says how many calls it covers.

## Outcome

### Deviations from the plan

- **"Live since" counts from the return** to the live version: the first call on it
  after the agent last ran any other version. So going back from 8 to 7 does not show
  7's first date from weeks before. Found by `/code-review`.
- **A third party's turn ends the reply gap.** After a transfer, the agent's next turn
  is not measured from the caller's last words. Found by `/code-review`.
- **The Calls tab** is the Calls page's own list. The loader moved to
  `components/calls/calls-list.tsx` and serves both. On the agent page it has no page
  bar, Agent filter or Agent column, and the agent page's period picker drives it.
- **Systems show the workflow's name and version id** ("booking-flow · version …"),
  not "v7": n8n gives an id, not a number.
- **The chart's title is "Latency",** with the period and how many calls it covers. Its
  day labels come every 7 days, or every 14 over 90 days.
- **The status table** marks the Agents page Done (#201). The decision log gains the
  latency answer, quoted.

### Check results

`make check` on the final tree. `pnpm build` also succeeds, with `/agents` and
`/agents/[id]` among the routes.

| Step | Result |
|---|---|
| Plan present and complete | ok |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

**New tests in `test_agent_page.py` (7):**

- reply gaps: an overlap, an unanswered caller turn and a third party's turn are not
  gaps; the median per call;
- the page:
  - name, platform and type;
  - the live version and since when;
  - calls, latency and the calls it covers;
  - 30 or 7 days;
  - the peak;
  - a version mark;
  - the spec state;
- latency on the Agents list, with none for a quiet agent;
- "live since" after a return to an older version;
- systems: a workflow with its latest version;
- another workspace and an unknown agent;
- `get_agent` and `list_agents` latency through MCP.

**MCP server:** `get_agent` is listed as read-only.

**Played through on a running backend** (port 8027, local database). The throwaway
agent was a conversational flow on versions 7 and 8, with three calls whose reply gaps
were 1.0, 1.4 and 2.2 s, and a workflow.

| # | Request | Came back |
|---|---|---|
| 1 | `GET /agents/list` | Conversational flow, 3 calls, latency 1.53 s |
| 2 | `GET /agents/{id}/page` | 200; live 8 with since; the model; the workflow at its latest version; 3 calls; latency 1.53 over 3; peak 2.2; mark "Version 8"; 30 days |
| 3 | `period=7d` | 7 days, 3 calls |
| 4 | `GET /calls?agent_id=…` (the Calls tab) | 3 calls |
| 5 | An unknown agent | 404 |
| 6 | MCP `get_agent` | Latency 1.53, 2 next steps, 3 rules |

The backend log had no errors. The throwaway data was deleted afterwards.

**`/code-review` (high) raised four findings:**

- **Fixed:** "live since" after a return to an older version.
- **Fixed:** third-party turns inflating reply gaps.
- **Fixed:** the workflow version shown as a cut "v" plus id.
- **Not fixed:** latency reads every turn of the period on each request. This is the
  risk the plan names; storing a call's latency when it is checked is the follow-up if
  it gets slow.

**For Dmytro to check on screen** (app.connexity.ai after merge, the demo workspace):

1. **Agents:**
   - a row opens the agent, with a hover;
   - Latency ("1.2 s", or "—" with none) between Agent and Calls.
2. **The agent page:**
   - the back arrow and the name;
   - "No spec" until one is written;
   - "Retell · Single prompt · version 14, live since 6 Nov";
   - the period picker.
3. **Tabs:** Overview and Calls, with the calls count. No Issues, Spec or Tests.
4. **Overview:**
   - the Calls and Latency tiles;
   - Details: platform, type, live version, model, and the workflows it used;
   - **"Latency":** bars per day with 0, middle and top labels, day labels, and a
     dashed mark at each new version.
5. **Calls tab:** this agent's calls, with no Agent column or filter. Search, Result,
   Category and Show more work.
6. **Dark and light.**

### Not done

- **Score, critical issues, the Issues, Spec and Tests tabs,** a latency goal and
  "failing" systems (later, as decided).
- **Storing latency per call,** unless it becomes slow.
- **The screens were not looked at by the session.**
