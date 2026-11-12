# Prompt for Claude Design: Action items and the agent's spec

Paste everything below the line into the existing Connexity project in Claude Design.

---

Add a new page, **Action items**, and a **Spec** section on the agent profile, in dark and light, using the existing design system, sidebar and page bar.

## Context

Every agent has a **spec**: what the agent is supposed to do, as plain rules. It is inferred from the agent's prompt the moment the agent is connected, so no agent is ever without one. Each agent version (every prompt change) has exactly one spec.

When calls show behaviour the spec does not cover, Connexity creates a **clarification**: a multiple-choice question for the person or their AI assistant. Once answered, the answer becomes part of the spec. The assistant can answer clarifications itself through MCP; the person sees who answered.

## Sidebar

Add **Action items** right after Home: Home, Action items, Agents, Roadmap, Issues, Settings. It shows a count of open items next to its name, in muted text.

## Screen: Action items

One place, across all agents, for everything that needs the person's input. Only things that need input: plain alerts do not belong here.

1. **Page bar:** "Action items".
2. **Number tiles:** Open 12, Critical 2, Answered this week 9, Parked 31.
3. **The list, most important first.** Show the top items only; the rest wait behind a quiet "38 more" line. A fleet can have hundreds of open clarifications, and the person must never face them all at once. Importance comes from how many calls the behaviour affects, how recent it is, whether it touches money, safety or compliance, and whether a critical issue depends on it.
4. **A clarification item:**
   - the agent's name and a severity badge when it is critical
   - the question in one plain sentence: "Car service booking offered a free courtesy car on 14 calls. Is it allowed to?"
   - the evidence in one muted line: "14 calls since 3 Nov · not covered by the spec of version 14", with a link to open a call
   - the answers as two to four buttons (a, b, c, d), for example "Yes, always", "Only for repairs over $500", "Never"
   - a quiet "Park" action for when it is not important right now
5. **Other item types** that need input share the same card layout with their own action, for example an incident waiting to be closed with a reason.
6. **Answered and Parked** sit below the list as two collapsed sections with their counts. An answered item shows the chosen answer and who answered: "Answered by your assistant, 10 Nov" or "Answered by Alex, 9 Nov". A parked item can be reopened.

## Agent profile: Spec section

Add a **Spec** section to the agent profile, after the details card.

1. **Header:** "Spec · version 14", with a version picker on the right to compare with an earlier version.
2. **The rules**, grouped by value area (the same areas as the Roadmap): each rule is one plain sentence, for example "Never quote a price above the seller's asking price". Under each rule, in muted text, where it came from: "From the prompt" or "From a clarification, answered by your assistant on 10 Nov".
3. Rules that matter for money, safety or compliance carry a small marker, so they stand out.
4. **Comparing versions:** picking an earlier version shows the difference in place: rules kept (plain), added (marked "Added"), dropped (struck through, marked "Dropped"). Rules are never edited; a new version brings a new spec.
5. **Answers carry over.** Rules that came from answered clarifications move into the new version's spec unchanged, marked "Carried over". When the new prompt contradicts one of them, the rule is marked "In conflict" and a new clarification about the conflict appears in Action items, quoting both the earlier answer and the new prompt.
6. A line under the header shows how many clarifications for this agent are open, linking to Action items filtered to the agent.

Read only: no editing of rules on screen. The spec changes only through a new agent version or an answered clarification.

Placeholder agents: Insurance renewals, Restaurant reservations, Car service booking, Clinic after-hours, Dental reception. All numbers and names are placeholders.
