# Issues page

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Issues page" (10.09, Stage Check).
- **Design:** `designs/screens/Connexity Issues.dc.html` (Claude Design export) for how
  the page looks. Prompts: `designs/10-issues.md` (Issues page part) and
  `designs/12-adjustments.md` items 1 and 8. Where they differ, the screen wins.
- **MCP:** extends `list_issues` with the page's search, filters, period and tiles. No new
  tool.

## Goal

A person opens **Issues** in the sidebar and sees the workspace's issues:

- tiles at the top;
- one search field and filters;
- the issues grouped by the fixed categories, worst first inside each group.

The assistant can list and filter issues the same way through `list_issues`.

From the roadmap: "The Issues page per workspace: tiles, search and filters, issues
grouped by category, worst first. No single issue page yet, so rows are not clickable
and Archive waits for it. MCP: list and filter issues the same way."

## What exists today

- **Issues are stored and grouped** (slice 2.3, #192, #193). An issue is one check on
  one agent with one key.
  - Its category comes from its check (#191).
  - It is Critical when any of its findings fails the call, otherwise a Warning.
  - It says whether a rule or a model found it.
- **No web route lists a workspace's issues.**
  - The web API has `GET /agents/{id}/issues` (1.x shape, no filters), `GET /issues/{id}`
    and `PUT /issues/{id}/state`.
  - MCP has `list_issues(workspace_id, agent_id?)`: worst first, paged, no search or
    filters.
- **The stored states still have their old names:** `regressed` and `accepted`. Dmytro
  renamed them on 2026-11-12 to Reopened and Archived (decision log), and the design
  uses the new names.
- **The Calls page (#194)** is the pattern for the screen: a server component reads the
  generated SDK, the filters live in the address, and the period picker offers 7, 30 or
  90 days.

## Changes

### Backend

`GET /api/v1/issues` answers for the signed-in person's open workspace.

**Tiles** follow the agent filter and the period only, like the Calls page:

- **Open:** open and reopened issues.
- **Critical:** open or reopened issues that are Critical.
- **Reopened.**
- **Resolved:** issues resolved in the period.
- **Calls affected:** distinct calls in the period with a finding from an open or
  reopened issue, "of" all the workspace's calls in the period.

**Rows,** grouped by category in the categories' fixed order. A category with no
matching issues is left out.

- Inside a group, worst first: Critical or Reopened first, then by calls affected in the
  period, then most recently seen. This is the design's order.
- Each row shows:
  - the title: the check's name and the key, as on the Calls page, for example
    "Booking with missing or placeholder details: schedule_appointment";
  - the agent;
  - Critical or Warning;
  - calls affected in the period, with the share of that agent's calls in the period
    ("38 calls · 3%");
  - the status: Open, Reopened, "Resolved in version 15" (or "Resolved" with no
    version) and Archived;
  - when it was last seen.
- Each group shows its issue count, calls affected and how many are critical.

**Filters and search:**

- **Search** (one field) matches words in the title, or an issue's full id.
- **Filters:** agent, category, severity (Critical, Warning), status (Open by default,
  which includes Reopened; then Reopened, Resolved, Archived), and the period (last 7, 30
  or 90 days, default 30).
- **Which issues a period shows:** open and reopened issues always show. A resolved issue
  shows when it was resolved in the period, and an archived one always shows under its
  filter.

**The whole list comes in one answer, with no paging.** A workspace has tens of issues,
not thousands, and grouping needs all of them. The answer is capped at 500 and says when
it was cut.

**`list_issues`** takes the same `query`, `agent_id`, `category`, `severity`, `status` and
`period`.

- It answers the tiles and the issues, worst first, still paged by cursor.
- Its `data` becomes `{tiles, issues}`, the same shape change `list_calls` made.
- Each issue keeps `found_by`, and gains `calls_affected` for the period next to
  `calls_total`.

**State names (question 1).** `regressed` becomes `reopened` and `accepted` becomes
`archived`:

- in the stored values, through a migration that rewrites the existing rows;
- in the API, MCP, `set_issue_state` and the docs.

Archiving keeps today's behaviour: a reason is required. "Until it gets worse" waits for
the single issue page.

### Frontend

- **Issues in the sidebar,** in its decided place (Home, Incidents, Action items, Agents,
  Calls, Roadmap, Issues, Settings). That means after Calls among the pages built so far.
- **The Issues screen, as the design export shows it:**
  - the page bar with "Issues" and the period picker;
  - the five tiles;
  - search ("Issue title or ID") and the Agent, Category, Severity and Status filters,
    with "Clear";
  - the column header and the category groups, collapsed to their name, count, calls
    and critical badge. A group opens on click, and every group opens while a search is
    typed;
  - "No issues match" with "Clear the search and filters".
- **Reopened stands out** in the accent colour, "Resolved in version …" is green and
  Archived is quiet, as in the design.
- **Left out, because it does not work yet (rule 14):**
  - **Rows open nothing.** The single issue page is 10.1, so rows are not links and have
    no hover state.
  - **The Milestone column.** There is no roadmap yet.
  - **Archive.** It waits for the issue page.

### Docs

- `docs-internal/checks-and-incidents.md` and `docs-internal/data-model.md` use the new
  state names.
- The MCP issues guide describes the filters and tiles.
- `docs-internal/mcp-architecture.md` gets the new `list_issues` arguments.

## Decisions

Decided by Dmytro:

- Issue states are open, resolved in a version, reopened and archived (2026-11-12).
- The sidebar order (2026-11-12). Categories are a fixed set (2026-11-12).
- The design wins over the prompts (roadmap entry).
- Rows are not clickable, and Archive waits for the issue page (roadmap entry).
- Remove Active incidents from the Issues page (`12-adjustments.md` item 8).

Proposed by Claude:

- Tiles follow the agent filter and the period only.
- Period rules: open issues always show, resolved ones by their resolve date, and
  archived ones always under their filter.
- A row's percentage is of its agent's calls in the period, matching MCP's
  "in N of M calls". The design shows a share of the whole fleet.
- One answer with no paging on the web, capped at 500. MCP stays paged.
- A title is the check's name plus its key, until the issue type library gives better
  sentences.
- The Milestone column is left out until the roadmap exists.

## Questions

1. **Rename the stored states now?** Recommended: yes, `regressed` becomes `reopened` and
   `accepted` becomes `archived` in the database, API and MCP in this pull request. It is
   one small migration, and the page, its filter and `list_issues` then use the same
   words. The alternative is renaming only on screen, which leaves two names for one
   state.
2. **The percentage on each row:** a share of the agent's calls (recommended), or a share
   of all the workspace's calls, as the design does?

## Done when

- `make check` passes. Backend tests cover:
  - only the open workspace's issues;
  - grouping in category order;
  - worst first inside a group;
  - each filter, the search by title and by id, and the period rules;
  - the tiles, with the tiles ignoring every filter except agent and period;
  - calls affected in the period, and the share;
  - the state rename: the migration and `set_issue_state` with the new names;
  - `list_issues` with the new filters and tiles, an unreachable workspace, and paging.
- Played through on a running backend through the API and MCP.
- **For Dmytro to check on screen** (app.connexity.ai after merge, the demo workspace):
  - Issues is in the sidebar after Calls;
  - the tiles match the demo workspace's issues;
  - the groups are in category order, collapsed, with counts;
  - search and each filter narrow the list, and "Clear" restores it;
  - rows do not open;
  - dark and light both look like the design.

## Out of scope

- **The single issue page, Archive and its dialog:** 10.1.
- **Milestones on rows:** these wait for the roadmap.
- **An Issues tab on the agent profile:** there is no agent profile yet.
- **Changing how issues are found or grouped.**
- **Removing `GET /agents/{id}/issues`.** It is 1.x, but `REBUILD.md` does not list it
  for deletion, so it stays unless Dmytro says otherwise.

## Risks

- **Titles from the check plus a key are plain.** For example, two issues read
  "Booking with missing or placeholder details: schedule_appointment" and
  "…: book_table".
- **Search by title runs in memory,** because titles come from the check registry, not
  the database. That is fine at tens of issues per workspace.
- **The rename migration rewrites stored state values.** The hosted database has a few
  issues, and none are regressed or accepted that I know of, but the migration handles
  them either way.

## Outcome

### Deviations from the plan

- **The questions were answered as recommended** ("Accept, build", 2026-11-13). The
  stored states are renamed in this pull request, and a row's share is of its agent's
  calls in the period.
- **The migration is not covered by an automated test.** The repo has no pattern for
  data-migration tests, so it was played through by hand on the local database. Three
  issues were set to the old names, then upgraded, downgraded and upgraded again (table
  below), and then set back.
- **`list_issues` answers `{tiles, issues}`.**
  - Each issue drops `type` and `first_seen_at`; `check_type` replaces `type`.
  - Each issue gains `key` and `resolved_version`.
  - `calls_affected` and `calls_total` now count the period, not all time.
- **`crud.list_workspace_issues` no longer sorts.** The order lives in
  `app/services/issue_list.py`, found by `/code-review`.
- **The Calls page's filter button moved** to `components/common/picker.tsx`, so both
  pages share it. It gained `highlighted`, so a status other than Open shows as set.
- **The sidebar icon for Issues** is the inbox icon from the Sidebar design.

### Check results

`make check` on the final tree. `pnpm build` also succeeds, with `/issues` among the
routes.

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

**New and changed tests:**

- **`test_issues_list.py` (4 new):**
  - grouping in category order, worst first, the share, a group's distinct calls, and
    the tiles;
  - each filter and the search by title and by id, with the tiles unchanged;
  - resolved, archived and reopened, calls affected per period, and a resolved issue
    outside the period;
  - another workspace, not signed in, and the old state name refused.
- **`test_mcp_issues.py`:**
  - the new answer shape and tiles;
  - search and filters (1 new);
  - calls placed inside the period.
- **`test_issues.py`:** the existing state tests now use `reopened` and `archived`.
  `test_an_issue_can_be_reopened_and_cannot_be_set_to_regressed` is renamed to
  `..._opened_again_and_cannot_be_set_to_reopened`. It checks the same thing under the
  new names.
- **MCP server:** `list_issues` sends its search and filters and reads the tiles.

**Migration, by hand on the local database:**

| Step | Issue states |
|---|---|
| Before, with three issues set to the old names | open 6, regressed 2, accepted 1 |
| After `upgrade` | open 6, reopened 2, archived 1 |
| After `downgrade` | open 6, regressed 2, accepted 1 |
| After `upgrade` again | the three issues set back to open; `alembic check` clean |

**Played through on a running backend** (port 8027, local database). The throwaway
workspace had two agents:

- 6 invented calls in the last 30 days, plus one 40 days old;
- booking problems and failed tool calls.

| # | Request | Came back |
|---|---|---|
| 1 | `GET /issues` | Tiles open 4, critical 4, calls affected 4 of 6. Booking (3 issues, 4 calls, 3 critical), then Tools and integrations. Worst first: 3/4, 1/2, 1/4 |
| 2 | `severity=warning` | No groups; tiles unchanged |
| 3 | `q=two bookings` | The duplicate-booking issue |
| 4 | `agent_id` = the second agent | 1 issue; tiles open 1, calls 2 |
| 5 | `period=90d&category=tools_and_integrations` | The tool issue on 2 of 5 calls |
| 6 | Not signed in | 401 |
| 7 | `status=accepted` (old name) | 422 |
| 8 | Archive without a reason | 422 |
| 9 | After resolving one issue in v15 and archiving another | Open 2, resolved 1. `status=resolved` shows "v15"; `status=archived` shows the archived one |
| 10 | MCP `list_issues` | Same tiles; 2 issues with `found_by` rule and 3 of 4, 1 of 2 |
| 11 | MCP `limit=1` | 1 issue and a cursor |
| 12 | MCP `status=resolved` | The resolved issue |
| 13 | MCP `query` with no match | "No issue matches…" next step |
| 14 | MCP, another workspace's id | 404 |

The backend log had no errors. The throwaway users, workspaces, agents, calls and
issues were deleted afterwards.

**`/code-review` (high) raised six findings:**

- **Fixed:** cutting the list at 500 kept the first categories instead of the worst
  issues.
- **Fixed:** the Status filter did not look set when it was not Open.
- **Fixed:** the period table was duplicated from the Calls page.
- **Fixed:** the open-and-reopened states were defined twice.
- **Fixed:** the issues were sorted twice.
- **Not fixed:** the page waits with an empty fallback instead of a skeleton, the same
  as the Calls page.

**For Dmytro to check on screen** (app.connexity.ai after merge, the demo workspace):

1. **Issues** is in the sidebar after Calls, with the inbox icon, and opens the page in
   dark and light, matching the design (no Milestone column).
2. **The tiles:** Open, Critical (in colour), Reopened, Resolved, and Calls affected
   "of" the workspace's calls in the last 30 days.
3. **The groups:** Booking and any other category with issues, collapsed, each reading
   "N issues · N calls" with a critical badge. A click opens a group.
4. **Each row:**
   - the title with its key;
   - the agent;
   - Critical or Warning;
   - "N calls · N%";
   - Open, Reopened (dark chip), "Resolved in version …" (green) or Archived;
   - "2 hours ago".
5. **Rows do not open anything,** and they have no hover state.
6. **Search and filters:**
   - typing words of a title and pressing Enter opens the matching groups;
   - Agent, Category, Severity and Status each narrow the list;
   - "Clear" restores it;
   - "No issues match" offers to clear.
7. **The period picker** changes the tiles and the calls counts.

### Not done

- **The single issue page, Archive and its dialog:** 10.1.
- **The Milestone column:** it waits for the roadmap.
- **A loading skeleton** for the page, as on the Calls page.
- **The screens were not looked at by the session.**
