# Prompt for Claude Design: Agents and agent profile

Paste everything below the line into the existing Connexity project in Claude Design.

---

Add two screens to Connexity, in dark and light, using the existing design system, sidebar and page bar: Agents, and the agent profile it opens.

## Agents

The place to compare agents: which are good and which are bad. Home keeps its own agents table unchanged; this page is the full comparison.

- Page bar: "Agents", muted caption "Retell · synced 5 minutes ago", period picker on the right.
- One table, one row per checked agent, worst first. Columns: Agent (platform and type underneath in muted text, e.g. "Retell · conversational flow"), Score, Critical issues (count, in critical colour when above zero), Latency (average, in warning colour when over the agent's goal), Calls.
- Clicking a row opens that agent's profile. Nothing else on the page.

## Agent profile

Same sidebar, with Agents selected.

1. Page bar: the agent's name, muted caption "Retell · conversational flow · version 14, live since 6 Nov", period picker.
2. Number tiles: Score 41, Calls 96, Latency 1.0 s, Critical 2, Issues 5. Label and value only.
3. Details card, read only: platform, agent type (single prompt or conversational flow), live version and since when, model, and the systems the agent uses with their versions, e.g. n8n workflow "quote-lookup v7" (1 failing), CRM "GoHighLevel". No prompt text, no settings, no editing.
4. Quality and latency over time: the score and the average latency across the period, with a mark at each new version of the agent, so a version that made things worse stands out.
5. Issues: this agent's open issues, critical first. Each row: severity badge, the issue in one plain sentence, its value area (the same areas as the Roadmap), calls affected, first seen. One agent can have hundreds of issues, so group the list by value area, each group collapsed to its name and count and expandable. Rows lead to the issue; a single call is reached from an issue, never listed here.

Placeholder agents: Insurance renewals, Restaurant reservations, Car service booking, Clinic after-hours, Dental reception. All numbers are placeholders.
