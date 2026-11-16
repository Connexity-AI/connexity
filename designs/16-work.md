# Prompt for Claude Design: the Work page

The Work page as designed on 2026-11-16, after a first draft and many adjustments (some
made directly in Claude Design). It replaces the Roadmap page, the "Now" part of prompt
15, the Action items page, and the suggested-answers screen of prompt 14. Pasted as one
prompt into a fresh project, it should give the screen exported as
`screens/Connexity Work.dc.html`. The decisions behind it, with Dmytro's words, are in
[`docs-internal/work.md`](../docs-internal/work.md); where the two disagree, that doc
wins.

Where the 2026-11-16 export differs from this prompt, build to the prompt:
- the waiting row's marker is a warm dot in the export, a warm pause icon here;
- the export writes "blocks:" in lowercase on the row, and "Up next" in the side panel
  for To do tasks; the words are "Blocks" and "To do";
- the waiting row still links to the Action items page, which Work replaces.

---

Replace the **Roadmap** page with a page called **Work**, in dark and light, within the existing design system, sidebar and page bar.

Think as a very good product designer. This page will also be used in sales, so it should feel calm, simple and obvious: one glance tells the story "my AI assistant is working through my agent's work, in the order I want, and it calls me when it needs me."

## The sidebar

- **Work** is the first item, and the page a person lands on after signing in. It carries a small warm count of what waits for the person.
- **Home** is renamed **Dashboard** and comes second, its content unchanged.
- **Action items** is removed: what needed the person now shows on Work.
- The rest stays: Incidents, Agents, Calls, Issues, Settings, and the Readiness ring at the bottom.

## The one idea

**The page is one ordered list of the assistant's tasks.** The assistant works down it from the top. A task's state, including when it waits for the person or is blocked, is shown on the task itself: there are no separate sections for assistants, waiting items or a plan.

## The page

1. **Page bar:** "Work", with a muted, dotted-underlined line "2 sessions working". Hovering it shows the assistants and their status. No cards for assistants.
2. **"Assistant tasks"**, with one muted line: "Your assistant works down this list from the top. You can reorder what hasn't started."
3. **Two groups, each a card with rows:** a small label "In progress", then a small label "To do".
4. **"3 done"**, one collapsed line with a check icon, which expands into short result rows.

## A row

- **A marker column** on the far left: a small spinning ring for a task in progress, a warm pause icon for one waiting for the person, a lock for one that is blocked. To do rows show a drag handle there on hover.
- **A type icon** in a soft tinted square, from the design system's icon set, so the eye can sort the list without reading:
  - **Onboarding:** a flag
  - **Clarifications:** a question mark
  - **Issue fix:** a wrench
  - **Setup:** a gear
  - Defined for later: **Incident** (a siren or alert), **Spec** (a document), **Calls to review** (a phone), **Tests** (a beaker)
- **The task in one plain sentence:** "The booking tool fails".
- **A muted second line:** the type word, then the details: "Issue fix · Critical · 23 calls", "Clarifications · Car service booking", "Setup". Severity is a quiet colored word, not an icon.
- **On the right, for a task in progress:** a chip with an initial avatar, the assistant and the session: "Alex's Claude Code · Onboarding".
- **Click a row** to open a side panel: its state, the task, then type, agent, assistant, session ("The Claude Code chat that ran the onboarding"), latest step and when, worked on for, then **Blocks** and **Blocked by** sections, then links to the agent, the issue or the calls.

## Waiting for you

A task that needs the person stays in **In progress**:
- a faint warm tint and a thin warm bar on its left edge, and the warm pause icon;
- on the right, a warm chip "Waiting for you" in the same shape as the assistant chip, with a quiet text link under it ("Answer questions →"). No filled button;
- its second line names what it blocks: "Clarifications · Car service booking · Blocks: The same booking is made twice + 1 more".

**Questions are answered right on Work, by the person.** Connexity shows no answers suggested by an assistant: an assistant that has suggestions asks in its own chat. A fix has fewer than four questions. "Answer questions →" opens them under the row, one card at a time: the question in one plain sentence, why it was asked in one muted line ("Seen on 9 calls"), the choices as large tappable options plus "Something else" with a text field, and "2 of 3" with back and skip. After the last card the row leaves the list, the answers go into the agent's spec, and the blocked tasks unlock. Answers given do not appear on Work beyond one row in "done".

## Blocks and Blocked by

Always these two words, never "holds up" or "after".
- **A task can block several.** The blocking task names them in its second line and lists them in its side panel under "Blocks".
- **A blocked task shows it on its own row:** the lock in the marker column (warm when the task it waits for is waiting for the person, muted otherwise), its title and icon slightly dimmed, and a third muted line "Blocked by: Answer 3 questions about bookings" that links to that task. Its side panel lists it under "Blocked by", with the blocking task's state.
- **Hovering either side highlights the other** with the thin warm bar; the other rows dim slightly.

## The scenario

One workspace, one agent, **Car service booking**, and one assistant, Alex's Claude Code.

**Frame 1, "Onboarding · no assistant yet"** (right after sign-up):
- Page bar: "Work", muted "No assistant connected".
- In progress: "Connect your AI assistant" · Onboarding · Waiting for you · link "Show how →". Its side panel shows the steps: copy the Connexity MCP address, add it to Claude Code or another assistant, sign in, and one line "From here on, your assistant does the setup with you."
- To do, each blocked by the step before: "Connect your voice platform", "Add the agents to watch", "Scan recent calls", "Write the spec for each agent".

**Frame 2, "Onboarding · assistant working":**
- Page bar: "1 session working".
- In progress: "Connect your voice platform" · Onboarding · Alex's Claude Code · Onboarding.
- To do: "Add the agents to watch" (Blocked by: Connect your voice platform), "Scan recent calls" (Blocked by: Add the agents to watch), "Write the spec for each agent" (Blocked by: Scan recent calls).
- Done: "1 done" · "Assistant connected · Alex's Claude Code".

When the last onboarding step is done, the list continues straight into the regular tasks. No separate onboarding page, wizard or progress ring on Work.

**Frame 3, "Working"** (after onboarding: the spec is written and the first scan found 2 critical and 3 regular issues; the assistant asked most of its questions in its chat, and 3 are left for the person):
- In progress:
  1. "Answer 3 questions about bookings" · Clarifications · Car service booking · Waiting for you · Blocks: The same booking is made twice + 1 more
  2. "The booking tool fails" · Issue fix · Critical · 23 calls · Alex's Claude Code · Onboarding
  3. "Connect to Slack" · Setup · Alex's Claude Code · Setup
- To do:
  1. "The same booking is made twice" · Issue fix · Critical · 9 calls · Blocked by: Answer 3 questions about bookings
  2. "Choose the incident channel the assistant watches" · Setup · Blocked by: Connect to Slack
  3. "Connect the agent's backends" · Setup
  4. "Write tests for the spec" · Setup · Blocked by: Answer 3 questions about bookings
  5. "Turn on the deployment gate" · Setup · Blocked by: Write tests for the spec
  6. "Turn on automatic roll back" · Setup
- Done: "3 done" · "Onboarding finished · Alex", "Spec written for Car service booking · version 1 · Alex's Claude Code", "First scan: 5 issues found · Connexity".

**Frame 4, "Answering"**: frame 3 with the questions open under the waiting row, the second card showing.

**Frame 5, "Answered"**: frame 3 after the last card, the questions gone and the blocked tasks unlocked.

**Frame 6, "Details"**: frame 3 with the side panel open on the waiting task, its "Blocks" section listing both blocked tasks.

**Also show:** hovering the waiting row in frame 3, with both blocked rows highlighted.

## Avoid

- Separate sections or cards for assistants, waiting items, a plan or goals. Goals and a zoomed-out roadmap are left out for now.
- More than two lines per row (three when blocked); latest steps and timers in the row (they belong in the side panel).
- Answers suggested by an assistant, and a confirm screen for them.
- Time estimates or predictions of how long a task will take.
- Checkboxes, "add task", a kanban board, assigning a task to an assistant.
- Tasks from other workspaces.

Placeholder agent: Car service booking. Placeholder person: Alex. All names and numbers are placeholders.
