# Work: task states, Done and refresh

- **Owner:** Dmytro
- **Slice:** Roadmap 10.194, from testing feedback 2026-11-18 (items 2 to 6)
- **Design:** `designs/screens/Connexity Work.dc.html` from design review 16 (views
  "working", "quiet task open", "done open", "refreshing", "hover"), and
  `Connexity.dc.html`.
- **MCP:** `move_task` is extended: the assistant can put a task it holds back in To do.
  `get_next_task` and `list_tasks` answer the new states. The contract entry, input
  descriptions and the getting-started guide are updated.

## Goal

Make Work tell the truth about what each session is doing. Today:

- asking for the next task turns a held issue fix into "Waiting for you";
- a scenarios task the assistant finishes vanishes from every list;
- a session that stopped working keeps its task spinning forever;
- the page never refreshes on its own.

## Changes

**Task states (backend and MCP)**

- **"Waiting for you" is only for clarifications** (Dmytro, 2026-11-18: "Waiting for
  you IS ONLY FOR CLARIFICATIONS"). Nothing else waits:
  - **A held issue fix stays In progress with its session** when the session asks for
    its next task. It stays until the issue is resolved or archived (then it is done),
    or until the session puts it back. A session may hold a fix alongside its next
    task.
  - **"Connect your AI assistant"** sits first in To do, marked as the person's own step
    with "Show how →", with no waiting chip. The new design still shows it as waiting:
    for Dmytro to change in Claude Design.
  - **Existing waiting rows** (issue fixes) become In progress again, through a data
    migration. The waiting state is removed from the code.
- **`move_task` on a task the assistant holds** puts it back in To do (Decided: "extend
  `move_task` or `get_next_task` rather than a near-duplicate tool"; Dmytro, 2026-11-18:
  "Only back to To do").

**Done**

- **Every finished task shows in Done, with who did it** (Decided): scenarios written,
  specs, fixes, reviews, onboarding steps and answers. Each row links to what it
  changed, as in the design. Today only reviews and onboarding steps are recorded.

**Quiet sessions**

- **A held task whose session has not asked for its next task in 30 minutes** stops
  spinning and
  shows "No activity since 14:20", still assigned (Decided: "i like it"). The panel
  says the assistant hasn't called Connexity since then and the task stays with the
  session.
- **Activity is its own session's `get_next_task`** (Dmytro, 2026-11-18): each call
  stores the time on the tasks that session holds. Exact per session; a session working
  long on one task without asking for the next one shows quiet.

**Page (frontend)**

- **A refresh icon,** top right, with "Updated 2 min ago" (Asked by Dmytro). It turns
  once and reloads the list; nothing else moves.
- **No "Put back in To do" button** for the person (Decided: "it will confuse
  assistant").
- **Every clickable element shows the pointer cursor and a hover state,** set once in
  the base styles (Decided).

## Decisions

- **Decided (Dmytro, roadmap row 10.194):**
  - the assistant can put a task back through MCP, extending a tool;
  - every finished task shows in Done, with who did it;
  - the quiet state is "No activity since <time>", still assigned;
  - no button for the person;
  - a refresh icon;
  - pointer and hover everywhere.
- **Decided (Dmytro, 2026-11-18, answering this plan):**
  - "Waiting for you" is only for clarifications;
  - a held issue fix stays In progress;
  - "Connect your AI assistant" is in To do, marked as the person's;
  - `move_task` only puts a task back in To do;
  - quiet after 30 minutes;
  - activity is the session's own `get_next_task`.

## Done when

- Through the API, in tests:
  - a session that holds an issue fix and asks for its next task keeps the fix In
    progress, and gets its next task too;
  - nothing but clarifications is ever waiting;
  - `move_task` puts a held task back in To do;
  - a scenarios task the assistant finishes appears in Done with who did it;
  - a held task with no activity past the default answers as quiet, with its last
    activity time.
- On screen (Dmytro):
  - quiet rows and their panel;
  - the waiting chip on questions only, and "Connect your AI assistant" in To do;
  - Done rows for every kind of task, each linking to its work;
  - the refresh icon;
  - pointer and hover everywhere.

## Out of scope

- "Latest step" and "Worked on for" in the panel: Connexity has no step reports from the
  assistant yet.
- Alerting a session.

## Risks

- **A session that works long on one task without calling `get_next_task` shows quiet**
  while it is still working. The panel says only that it has not called Connexity.

## Outcome

### Deviations from the plan

- **The sidebar's waiting count** now counts only agents with open questions. It used to
  count the person's connect step and waiting fixes too.
- **Putting a task back is the assistant's alone.** The person's own move of a task an
  assistant holds is refused with "Another assistant is working on this task".
  `move_task` keeps its "only when asked" mark on `/mcp-docs` because reordering is
  still only on request; its description says putting back your own task is not.
- **Hover:** the pointer is set once in the base styles. The hover backgrounds stay in
  each component, since most rows and buttons already have one; the Work page's Done
  rows and question links gain theirs.
- **The panel shows "No activity since"** in place of the design's "Latest step", with
  the design's note, because Connexity gets no step reports from the assistant.

### Check results

`make check` (on main with #235): every step ok. `pnpm --filter web build`: ok. Route tests ran through the API on the local
database (`TestClient`), so no separate play-through server was used.

**Tests:**

- **`test_next_task.py`:**
  - after the session asks again, a held issue fix stays In progress, with its time
    seen, and the session gets a different next task;
  - nothing but questions is waiting.
- **`test_work_page.py`:**
  - "Connect your AI assistant" is first in To do, the person's, and the waiting count
    is 0;
  - the person cannot put back an assistant's task;
  - `move_task` through MCP puts the assistant's own fix back in To do, and another
    session can take it;
  - a task untouched for 31 minutes answers `quiet_since` and stays held, and its
    session's `get_next_task` clears it;
  - Done lists "Scenarios written for Night line" (who and session, linked to its
    Tests tab), "Calls reviewed for Night line" (linked to Calls) and specs (linked to
    Spec).

**MCP server tests:** 53.

### For Dmytro on screen

- **Work,** brand new workspace: "Connect your AI assistant" first in To do, with
  "Show how →" opening the connect help; no "Waiting for you" chip, and the sidebar
  count is 0.
- **Work,** with a fix in progress: it stays In progress with its session after the
  session takes its next task.
- **Work,** a session silent for 30 minutes: a still grey dot instead of the spinner,
  "No activity since 14:20" under the title, and the panel note. The caption reads
  "1 session working, 1 quiet".
- **Work, top right:** "Updated just now" and a refresh icon that turns once and
  reloads the list.
- **Work, "N done this week":** scenarios and reviews appear, each row opens its work
  (Spec, Tests or Calls tab, or the issue).
- **Anywhere:** the pointer over every link, button and clickable row.

### Not done

- **The Work design still shows "Connect your AI assistant" as waiting,** for Dmytro to
  change in Claude Design.
- "Latest step" and "Worked on for" (no step reports yet).
