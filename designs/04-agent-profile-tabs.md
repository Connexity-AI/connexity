# Prompt for Claude Design: agent profile in tabs, with the spec on its own tab

Paste everything below the line into the existing Connexity project in Claude Design. It changes the agent profile from prompts 02 and 03.

---

Split the agent profile into tabs, in dark and light, using the existing design system. A spec can have 100 or more rules, so it gets its own tab instead of a section.

## Tabs

Under the page bar (the agent's name, "Retell · conversational flow · version 14, live since 6 Nov", period picker), three tabs: **Overview**, **Issues**, **Spec**. Overview is open by default.

- **Overview:** the number tiles (Score, Calls, Latency, Critical, Issues), the read-only details card with the systems the agent uses, and quality and latency over time with version marks.
- **Issues:** the agent's open issues, critical first, grouped by value area, each group collapsed to its name and count and expandable.
- **Spec:** below.

The tab label shows a count where it helps: "Issues 5", "Spec 132".

## Spec tab

Built for 100 or more rules: the person should find their way in seconds without reading everything.

1. **A summary row of number tiles:** Rules 132, From the prompt 118, From clarifications 14, In conflict 1, Open clarifications 3 (linking to Action items filtered to this agent).
2. **Version line:** "Version 14 · live since 6 Nov" with a version picker on the right to compare with an earlier version. When comparing, the tiles become Kept, Added, Dropped, and a toggle "Show changes only" hides kept rules.
3. **Rules grouped by value area** (the same areas as the Roadmap), each group collapsed by default to its name, rule count, and markers for anything inside that needs attention (a rule in conflict, a newly added rule). Rules with no clear area go in a last group, "Other".
4. **Inside a group:** one row per rule: the rule in one plain sentence, a muted line with its source ("From the prompt" or "From a clarification, answered by your assistant on 10 Nov"), and a small marker for money, safety or compliance rules. Carried-over rules are marked "Carried over"; a rule the new prompt contradicts is marked "In conflict" and links to its clarification.
5. Rules in conflict and rules that touch money, safety or compliance sort to the top of their group.

Read only: no editing of rules. Spacing stays compact: a rule is a single row, not a card.

Placeholder agents: Insurance renewals, Restaurant reservations, Car service booking, Clinic after-hours, Dental reception. All numbers and names are placeholders.
