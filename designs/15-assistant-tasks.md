# Prompt for Claude Design: the assistant's tasks on the Roadmap

> **Superseded by [`16-work.md`](./16-work.md)** (Dmytro, 2026-11-16): the Work page
> replaces the Roadmap page and this "Now" part. Kept for the record; do not build from
> it.

Paste everything below the line into the existing Connexity project in Claude Design. It adds a "Now" part to the top of the Roadmap page; the milestones from the earlier roadmap prompt stay below it.

---

Add the assistant's tasks to the **Roadmap** page, in dark and light, using the existing design system, sidebar and page bar.

## Context

The team's AI assistant (Claude Code or similar) works through MCP. At the start of a session and after finishing each task, it asks Connexity for its next task, and Connexity hands it the single most important one. The person does not plan the assistant's work: Connexity sets the order, the assistant does the work, and the person approves where a decision is theirs.

- **Tasks come from what is happening.** An active incident, an unanswered clarification, an agent without a spec: each is a task until it is dealt with, and it disappears by itself when it is. Nobody writes or closes tasks by hand.
- **Two lanes, in a fixed order.** **Operational** comes first, always: (1) critical incidents, (2) clarifications, (3) specs to write or update, (4) calls to review. **Roadmap** comes when the operational lane is empty: the fixes in the milestones below, worst first, then tests to write and open Readiness steps.
- **One workspace.** Everything on this page belongs to the current client's workspace. Nothing from other workspaces appears.
- **In progress.** When an assistant takes a task, it shows as in progress with whose assistant took it, and no other assistant gets it.
- **Waiting for you.** Some tasks end with a decision only a person makes (confirming answers, closing an incident). The assistant does its part and asks the person in the chat; the task then waits for the person and also shows in Action items.

## The page, top to bottom

1. **Page bar:** "Roadmap", muted "Updated 2 minutes ago". No buttons.
2. **Number tiles:** In progress 1, Operational 4, Waiting for you 2, Done this week 23, then the existing milestone tiles.
3. **"Now":** one card, the most visible thing on the page.
   - **The task in progress:** its type as a small label ("Clarification", "Incident", "Spec"), one plain sentence ("Prepare answers for 3 clarifications on Car service booking"), the agent, and a muted line "Alex's assistant · started 12 minutes ago".
   - **Up next:** the next three tasks in order, one compact row each: rank, type label, the sentence, the agent, and for incidents and issues the calls affected ("14 calls"). A quiet "9 more" line opens the full list.
   - **Waiting for you:** the tasks that need the person, one row each with its action, linking to the item in Action items. Hidden when there are none.
   - **When the operational lane is empty:** the card says so in one line ("Nothing urgent. The assistant is working on the roadmap.") and shows the roadmap task in progress.
4. **Done:** one collapsed line, "23 done this week", expandable into rows: what was done, by whose assistant, when, and the result ("Spec written for Dental reception · version 4", "Incident closed by Alex").
5. **Milestones:** the existing roadmap from the earlier prompt, unchanged, under a small heading "Roadmap". The current milestone's fixes are the roadmap lane's tasks; a fix the assistant is working on shows the same "in progress" marker.

Connexity sets the order. **Operational tasks can never be reordered:** they show no drag handle. **Roadmap tasks can be reordered by the person:** in the milestones (the drag from the earlier prompt) and in Up next, where a roadmap task row has a drag handle and the "Move to" menu. A move changes what the assistant gets next.

## Avoid

- A to-do list the person maintains, checkboxes, or "add task".
- A kanban board.
- Tasks from other workspaces.
- A "send to assistant" button: the assistant asks for its tasks itself.

Placeholder agents: Insurance renewals, Restaurant reservations, Car service booking, Clinic after-hours, Dental reception. Placeholder people: Alex, Sam. All names and numbers are placeholders.
