# Work updates by itself

- **Owner:** Dmytro
- **Slice:** Roadmap 10.195
- **Design:** No UI change. The refresh icon and "Updated N min ago" from 10.194 stay.
- **MCP:** None needed. The assistant reads Work through `list_tasks` and
  `get_next_task`, which always answer the current state.

## Goal

Dmytro, 2026-11-19: Work tasks should update without a manual refresh ("useful but not
crucial"). While the Work page is open and visible, the following follow what the
assistant does, within a few seconds:

- the list;
- the counts;
- the done line;
- the sidebar's waiting count.

## Changes

- **Polling, not push** (Proposed in the row, Dmytro: "ok create a task"): it works the
  same on Supabase and on a plain Postgres, with no second auth path or row-level
  security. Server push (LISTEN/NOTIFY and server-sent events) comes later, only if
  polling feels slow.
- **Every 10 seconds** while the page is open and visible (Dmytro, 2026-11-19).
- **TanStack Query polling** (Dmytro, 2026-11-19: "TanStack Query polling"; a server
  re-render would reload the whole layout on every tick). The flow, following the
  `tanstack-streaming` pattern:
  - The Work page prefetches `/work` on the server into the query cache and hydrates
    it, so the first paint is unchanged.
  - The page then reads it with a query that refetches every 10 seconds
    (`refetchInterval`, not in background tabs, again on window focus): one `/work`
    request per tick.
  - A move by drag and the refresh icon refetch the query instead of re-rendering the
    whole page.
  - **The sidebar's waiting count** reads a query seeded from the layout's count. Each
    Work reload writes the new count into it, so the sidebar follows with no request of
    its own.
- **Only while it matters:**
  - reloads pause while the tab is hidden;
  - the page reloads at once when the tab or window regains focus;
  - a drag in progress is never interrupted.
- **Nothing jumps or closes:**
  - an open side panel stays open;
  - open question cards keep their place and what the person picked;
  - a move the person just made keeps showing until the server has it;
  - a task that disappears closes its panel.
- **"Updated just now"** follows each reload. The refresh icon still reloads at once.

## Decisions

- **Decided (Dmytro, roadmap row 10.195):** polling on any Postgres, not Supabase
  Realtime; paused in background tabs; refetch on focus; nothing jumps or loses an open
  panel or question card; the refresh icon stays.
- **Decided (Dmytro, 2026-11-19):** reload every 10 seconds.
- **Decided (Dmytro, 2026-11-19):** TanStack Query polling.

## Done when

- **Dmytro, on screen:** with Work open, the assistant takes or finishes a task, and the
  row moves within the interval without a click. The sidebar count follows.
- **Dmytro, on screen:** an open panel and an open question card survive a reload.
- **Dmytro, on screen:** a hidden tab makes no requests (network panel); focusing it
  reloads at once.
- Frontend lint, types and the build pass.

## Out of scope

- Live updates on other pages.
- Server push.

## Risks

- **Each open Work tab** works out the whole task list on every reload. The answer is
  bounded by the workspace's tasks. Watch the backend's latency on `/work` after
  release.

## Outcome

### Deviations from the plan

- **The query stays fresh for 5 seconds** (half a tick), so the copy the server
  prefetched is not fetched again as soon as the page loads.
- **Answering on the question cards** refetches Work at once, rather than waiting for
  the next tick.
- **A layout re-render** (after a move or an answer, which revalidates the layout) also
  writes its count into the sidebar's query, so neither source goes stale.

### Check results

`make check`: every step ok. `pnpm --filter web build`: ok. There are no
frontend tests in the repo; Dmytro checks the screen.

### For Dmytro on screen

- **Work with your assistant working:** a task taken or finished moves within about
  10 seconds with no click, and "Updated just now" follows. The sidebar's Work count
  changes with it.
- **Open a task's side panel,** or the question cards, and wait for a reload: they stay
  open, and the picks on the cards stay.
- **Hide the tab** (switch tabs) and watch the network panel: no `/work` requests.
  Come back: one reload at once.
- **Drag a To do row** and hold it: no reload while dragging. Drop it: the list reloads
  once with the new order.
- **The refresh icon** still reloads at once.

### Not done

None.
