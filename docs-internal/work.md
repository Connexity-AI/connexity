# The Work page

Work is where the person sees what their AI assistants are working on, what comes next,
and what waits for them, and where they change the order. It replaces the Roadmap page
and Action items, and it is the page a person lands on.

This doc records what was settled, with Dmytro's words, and what is still open. Only his
own words make something Decided. The design is
[`designs/16-work.md`](../designs/16-work.md) and the exported screen
`designs/screens/Connexity Work.dc.html`; where they disagree with this doc, this doc
wins. What `get_next_task` hands out is planned in the
"Next task for the assistant" pull request (`plans/2026-11-15-next-task.md`).

## Decided

| # | Decision | Dmytro's words | Date |
|---|---|---|---|
| 1 | The Roadmap page is replaced by **Work**: the manager's view of the AI assistants, who work like employees: what they work on now, what's next, and where the person changes direction. | "This is like a manager view where your ai assistant(s) are employees" · "lets start with Work" | 2026-11-16 |
| 2 | Not "Team": that word means seats and members. | "Team doesnt work cause its always used for team management (seats)" | 2026-11-16 |
| 3 | The page is one simplified list of tasks. Details open on demand. Nothing is split into separate sections for assistants, waiting items and next tasks. | "super simplified more like what tasks are in progress. They can open them for details" · "no natural for eye connection between current tasks and next tasks" | 2026-11-16 |
| 4 | It must look good enough for sales, within the design system. | "it should look nice cause it will be something i will use for marketing/sales … not asking to bend the design system" | 2026-11-16 |
| 5 | Assistants pull their tasks. Connexity and the person set the priority. | "the goal will be assistants pulling tasks, Connexity and humans prioritize it" | 2026-11-16 |
| 6 | ~~Operational tasks can't be reordered. Roadmap tasks can.~~ Replaced by 23. | "the roadmap tasks can be reorded but not the operational tasks" | 2026-11-15 |
| 7 | One workspace only. Assistants that span workspaces come later, as a separate kind of connection. | "for now i would skip to per workspace only" | 2026-11-15 |
| 8 | A task an assistant took is In progress, and others skip it. Stuck tasks get timer checks later. | "isnt it easier to put in progress if one of the assistant took it? … timer checks in future not needed now" | 2026-11-15 |
| 9 | A task that waits for the person stays under In progress, highlighted. | "Staying in In progress with the warm highlight" | 2026-11-16 |
| 10 | Connexity doesn't track session blockers (the assistant asking in its own chat). Waiting comes from Connexity's own data. Connexity applies dependencies itself. | "agree" (to: skip session blockers, derive waiting from data, apply dependencies silently) | 2026-11-16 |
| 11 | A blocked task shows that it is blocked, and the blocking task shows what it blocks. One task can block several. | "I need to know which tasks it's blocking" · "I need to see that that task is blocked too" · "one thing can block two or more tasks" | 2026-11-16 |
| 12 | Action items fold into Work. | "I want it to fold into Work" | 2026-11-16 |
| 13 | Connexity shows no AI-suggested answers. The person answers in the assistant's session, or manually in Connexity. | "I dont want to translate AI Assistant suggestions to Connexity - it becomes loop in a loop insanity … in connexity you can only manually answer" | 2026-11-16 |
| 14 | A fix's questions stay under 4 and are answered one card at a time on Work. | "we will try to keep it always less then 4 so we can show them one by one as tinder cards" | 2026-11-16 |
| 15 | Decisions are recorded but barely visible, mostly in the spec. | "We need to keep decisions yes but its uber low visibility … more needed in the spec" | 2026-11-16 |
| 16 | Goals are parked. They may later group the list or give the roadmap its structure. | "we need to park goals for now … need a thorough planning" | 2026-11-16 |
| 17 | No time estimates for assistant work. Goals tied to dates come later. | "try to avoid time estimates … in future we will allow to tie goals to dates" | 2026-11-16 |
| 18 | The wording is **Blocks** and **Blocked by**, on the row, in the side panel and on hover. Not "holds up" or "after". | "I also asked design to use Blocks and Blocked by vs other terms" | 2026-11-16 |
| 19 | Work is the first item in the sidebar. Home is renamed **Dashboard**. | "lets put the work on the top instead of Home and home will become dashboard" | 2026-11-16 |
| 20 | People land on **Work** after signing in, because onboarding lives on Work. | "Work because it will have onboarding screen" | 2026-11-16 |
| 21 | Onboarding steps are rows in the task list (the Onboarding type). Work gets its own onboarding state. | "onboarding steps as rows in the task list - we need one more screen for work for that state" | 2026-11-16 |
| 22 | The roadmap (the zoomed-out plan) is parked until after the demo. The Work list as designed is enough for the demo and first users. Brainstormed so far: horizons, outcome groups, Readiness milestones, dependency chains, intent in words, a Plan view. | "lets park roadmap after demo, its too nuanced … the simple version we have now is good for demo and first tries" | 2026-11-16 |
| 23 | Every task can be reordered except one In progress. | "All tasks can be reordered except of in progress" | 2026-11-16 |
| 24 | Connexity sorts; the assistant just gets its next task. The order: incidents always first, then Critical tasks, then setup tasks in Connexity's order, then all other issues and clarifications. A task that blocks a higher task sits above it. | "Incidents should go first always … Tasks that block high priority tasks should be obviously above them … The goal is that connexity does the sorting, AI assistant just gets next task thats it" | 2026-11-16 |
| 25 | All issues are tasks, Critical on top. | "all issues get in the work, just critical on the top" | 2026-11-16 |
| 26 | Which task blocks which, worked out by Connexity: an agent's open questions block every issue fix on that agent; its spec to write or update blocks its fixes and calls to review; each onboarding step blocks the next; the first scan blocks every spec. | "Accept, build" on `plans/2026-11-16-blocks.md` | 2026-11-16 |

## Proposed (in the design, not decided)

- An assistant is a named connection ("Alex's Claude Code"), and each session has a name ("Onboarding"). The row's chip shows "assistant · session".
- The assistant names its session in its MCP calls, and Connexity shows the name. Built in 10.125, keyed by the name: the stateless MCP adapter passes no session id.
- The task types and their icons: Clarifications, Issue fix, Setup, Incident, Spec, Calls to review, Tests, Onboarding.
- The side panel fields: type, agent, assistant, session, latest step, worked on for, blocks / blocked by, links.

## Open

2. **The Action items page (10.122, built).** Decision 12 means its answering moves into the cards on Work and the page goes away. When, and in which roadmap row?
3. **Questions per fix.** The spec after onboarding leaves 7 clarifications at once. Is the under-4 rule a limit on how many the assistant raises per fix, or must the cards also handle more?
4. **Does our MCP adapter pass the session id through?** No: it is stateless, so 10.125 keys sessions by their name.
5. **Connexity triggering an assistant** (a Slack thread, a routine webhook, a schedule). Brainstormed, not chosen.
6. **Regular issues.** Settled by decision 25.
7. **Setup rows.** Six setup tasks can bury the real work. Should they become one row, "Finish setup · 4 of 6"?
8. **Setup that needs a person** (signing in to Slack). Is it "Waiting for you" from the start?
9. **The sidebar counts** must match the list (incidents, what waits for you).
10. **Dashboard** keeps Home's content as it is?
11. **"Give before asking"** (`frontend/CLAUDE.md`, the lifecycle guide) says what needs the person is never first. Work puts a task waiting for the person at the top of In progress. Which rule wins on Work?
