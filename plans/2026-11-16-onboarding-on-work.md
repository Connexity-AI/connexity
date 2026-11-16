# Onboarding as tasks on Work

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Onboarding as tasks on Work" (10.129). It
  follows 10.128 (#216, merged).
- **Design:** `designs/16-work.md`, frames 1 ("Onboarding · no assistant yet") and 2
  ("Onboarding · assistant working"); `docs-internal/work.md` decisions 20 and 21.
  Screens: `designs/screens/Connexity Work.dc.html` and `Connexity Sidebar.dc.html`
  (the Readiness ring).
- **MCP:** nothing new. Onboarding steps already reach the assistant as tasks through
  `get_next_task`, and `get_readiness` stays.

## Goal

A new person lands on Work and sees the same list the assistant will work through: first
"Connect your AI assistant", waiting for them with how to do it, then the steps the
assistant takes with them, each blocked by the one before. When the last step is done,
the list goes straight on into the regular tasks. There is no separate onboarding page.

## What exists

- **The steps are tasks already** (10.124 to 10.126): Onboarding rows from the Readiness
  steps, each blocking the next, and the first scan blocking every spec.
  "Connect your AI assistant" waits for the person; an assistant asking never sees it.
- **`/` is the Readiness screen** until the first scan is done, then it opens Work
  (10.127). It explains connecting an assistant (`ConnectAssistant`): the Claude Code
  setup prompt, the MCP address for Claude.ai or ChatGPT, and a refresh until it
  connects.
- **No Readiness ring is built yet;** it is in the Sidebar design.

## Changes

### Landing

- **`/` always opens Work** (decision 20). The Readiness screen (`readiness-view.tsx`) is
  deleted (question 1). `ConnectAssistant` and `CopyField` move into the Work page's
  side panel.

### The onboarding rows

- **The rows take the design's titles:**
  1. "Connect your AI assistant";
  2. "Connect your voice platform";
  3. "Add the agents to watch" (today "Add the agents to watch and bring in their
     calls");
  4. "Scan recent calls";
  5. "Write the spec for each agent" (question 2).
- **"Write the spec for each agent"** is one Onboarding row while the first scan is not
  done, blocked by "Scan recent calls". After the scan, the agents' own spec tasks take
  its place.
- **"Connect your AI assistant"** keeps its warm "Waiting for you". Its link reads
  "Show how →" and opens the side panel. The panel has:
  - the steps: copy the Connexity MCP address, add it to Claude Code or another
    assistant, sign in;
  - `ConnectAssistant` (the setup prompt and the address), as on Readiness today, with
    its refresh while open;
  - the line "From here on, your assistant does the setup with you."

  When the assistant connects, the row leaves and "Connect your voice platform" is next.
- **`GET /work` gains:**
  - `mcp_url`, for the panel;
  - `assistant_connected`, for the page bar.

### The page bar and done

- **"No assistant connected"** in the page bar while none is (frame 1). "No assistant
  working" when one is connected but none holds a task, and "N sessions working" as
  today.
- **Done gains "Assistant connected · Alex's Claude Code",** dated by when it first
  connected, within the last 7 days (question 4).

### The sidebar

- **The Readiness ring** at the bottom of the sidebar, as designed: a small ring with
  "Readiness" and its percentage, from `get_readiness`'s number (question 3). It shows
  until Readiness is 100%. It links to Work, since the Roadmap it pointed at is parked.

## Decisions

- **Onboarding steps are rows in the task list,** and people land on Work. Decisions 20
  and 21, Dmytro: "onboarding steps as rows in the task list", "Work because it will
  have onboarding screen".
- **No separate onboarding page, wizard or progress ring on Work** (design).
- Everything under "Questions" is Proposed until Dmytro answers.

## Questions

1. **Delete the Readiness screen.** Rule 7 asks before deleting what `REBUILD.md` does
   not list. Recommend deleting it, as the row says ("Replaces the Onboarding screen"),
   and keeping its connect help in Work's side panel. `GET /readiness` and
   `get_readiness` stay for the number.
2. **"Write the spec for each agent" before any agent has calls.** It is a real step, so
   it is no placeholder (rule 14). It exists while the first scan is not done. Recommend
   showing it so the list reads as the design's frame 1. Without it, specs appear only
   after the scan, one per agent.
3. **The Readiness ring.** The row says the ring "stays", but it is only in the design.
   Recommend building it here, small: ring and percentage, linking to Work, shown until
   setup is done. The alternative is leaving the sidebar without it.
4. **"Assistant connected" in done.** Recommend dating it by the first token the
   workspace's assistant was given (refresh or personal access token). The done row then
   reads as the design's frame 2.
5. **The Onboarding screen's design** (`Connexity Onboarding.dc.html`). Recommend marking
   it superseded by Work in `designs/README.md`.

## Done when

- **Through the API,** in the route tests on the local database:
  - a new workspace's `GET /work` answers "Connect your AI assistant" waiting, then the
    four steps, each blocked by the one before, and `assistant_connected` false;
  - after a connection, the first step leaves, "Assistant connected" is done, and the
    voice platform is next;
  - after the first scan, "Write the spec for each agent" gives way to each agent's
    spec.
- **`make check` passes** once, before the pull request.
- **For Dmytro on screen:**
  - signing up lands on Work in frame 1's state;
  - "Show how →" opens the panel with the setup prompt and the address;
  - connecting moves on to frame 2;
  - the Readiness ring;
  - `/` opens Work.

## Out of scope

- Setup tasks beyond Readiness's four steps (Slack, backends, the gate): no source yet.
- A wizard or progress ring on Work (design).

## Risks

- **Losing the Readiness screen's detail,** such as "N calls without versions". Those
  facts go into the rows' second lines, where they exist.

## Outcome

### Deviations from the plan

- **`connected_assistants`'s lookup is split** into `_connections` (when, name, person)
  with `first_connection` beside it. Personal access tokens now say whose they are.
- **Review findings:**
  - **Fixed:** the onboarding rows now carry Readiness's fact ("2 agents · 40 calls") on
    their second line.
  - **Left as they are:**
    - "Assistant connected" in done is dated by the oldest connection still in use, so
      it leaves done if that token lapses;
    - every page reads Readiness for the ring.

### Check results

`make check`:

| Gate | Result |
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

`pnpm --filter connexity build` passes. While building, only the touched test files ran
(`test_work_page.py`, `test_next_task.py`, the readiness tests), then the full
`make check` ran once (CLAUDE.local.md). No separate play-through server: the route tests
send the same requests through the API.
- **A new workspace's `GET /work`:**
  - "Connect your AI assistant" is waiting;
  - then "Connect your voice platform", "Add the agents to watch", "Scan recent calls"
    and "Write the spec for each agent", each blocked by the one before;
  - `assistant_connected` is false.
- **After a personal access token is used:** the step leaves, "Assistant connected"
  is done ("…'s Claude Code"), and the voice platform is next and unblocked.
- **After the first scan,** "Write the spec for each agent" gives way to each agent's
  spec task. Before it, no agent has its own spec task.

**For Dmytro to check on screen:**
1. **Sign up or sign in to a new workspace:**
   - `/` opens Work;
   - the page bar reads "No assistant connected";
   - "Connect your AI assistant" is waiting, with "Show how →";
   - the four steps are under To do, each with its lock and "Blocked by: …".
2. **"Show how →"** opens the side panel with:
   - the three steps;
   - the Claude Code setup prompt and the Claude.ai or ChatGPT address (as Readiness had);
   - "From here on, your assistant does the setup with you."

   The panel refreshes until the assistant connects.
3. **Once connected:**
   - the row leaves;
   - "Connect your voice platform" is next;
   - "1 done" shows "Assistant connected · Name's Claude Code".
4. **The Readiness ring** at the bottom of the sidebar shows the percentage, opens
   Work, and is gone at 100%.
5. **An existing workspace:** `/` opens Work as before.

### Not done

- Setup tasks beyond Readiness's four steps (no source yet).
- The two review findings left above.
