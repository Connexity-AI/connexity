# Prompt for Claude Design: incidents and alerts

Paste everything below the line into the existing Connexity project in Claude Design. It adds the incident page, puts incidents at the top of Action items, and links incidents from the Issues page and the issue page (prompt 10).

---

Design **incidents** and how they reach people, in dark and light, using the existing design system, sidebar, page bar and the Action items card layout (prompt 03).

## What an incident is

An **incident** is one outage: a period when something was failing real calls. It can span several agents: when the same issue type with the same key (for example "Tool call failed: booking") starts failing on 10 agents at once, that is **one incident covering 10 issues**, not ten incidents. Only critical issues (those that fail calls) create incidents.

An incident is **Open** or **Closed**. It closes when the damage has stopped, which is not the same as the issue being fixed: a rollback, a backend coming back up, or a workaround can stop the damage while the issues stay open until a fixed version ships. Only a person closes an incident, with a cause and a reason; the assistant can propose it. If the same issue fails again after closing, a new incident opens, marked "2nd incident on this issue".

There is no Incidents page in the sidebar. Incidents are reached from Action items, the Issues page, the issue page, and alerts.

## Action items: incidents first

Action items holds only what needs a person to act, and its order is urgency. Add a **Now** tier at the very top, above clarifications, visually stronger than the rest, but calm: no flashing, no full-width red.

- **An open incident card:** "Incident · Booking tool failing", "4 agents · 31 calls failed · since 09:12", what changed just before ("Version 15 went live at 08:55"), and two actions: "Open incident" and "Close". When the assistant has proposed closing it, the card says so with the proposed cause ("Your assistant proposes closing: rolled back to version 14") and the person confirms or rejects.
- **A version live without passing its tests:** "Car service booking · version 15 is live but failed its tests", with "Open version" and "Accept with a reason".

Informational events (an incident grew, a failed gate was overridden, an incident was closed) never become Action items. They go to the team's channels and appear as lines in the timeline of the incident or version they belong to. The tile row gets one more tile at the front: **Failing now 1**.

## Screen: an incident

Lightweight, focused on this one period and its reach.

1. **Page bar:** "Incident", its title ("Booking tool failing"), Open or Closed, start time and duration.
2. **Number tiles:** Period (since 09:12 · 2 h), Agents 4, Calls failed 31, Callers 27, Time to detect 3 min, Time to close (once closed).
3. **Blast radius over time:** failed calls per 15 minutes across the period, stacked or split by agent, so it is clear whether the damage is growing or stopping.
4. **Agents and issues:** one row per agent in the incident: agent, its issue (linking to the issue page), calls failed, and whether that agent is still failing or has stopped.
5. **What changed just before:** versions that went live and tools that started failing, with times.
6. **Timeline:** opened, alert sent to Slack, more agents joined, rollback on Car service booking, last failure, closed by Alex with the reason. Filled in automatically; informational alerts show here.
7. **Affected calls:** the latest failed calls, same rows as the Calls page, each opening the call at the moment. "All 31 calls" opens the Calls page filtered to the incident.
8. **When closed:** how it stopped (rollback, fix in a version, outside recovery, workaround), the cause, who closed it and the reason.
9. **Actions:** "Close" (asks for how it stopped, the cause and a reason). Quiet "Merge" and "Split" in a menu, for correcting the grouping.

## Issues page and issue page

- **Issues page:** a **Failing now** section above the category groups, one row per open incident, linking to the incident page. Hidden when nothing is failing.
- **Issue page:** while the issue is part of an open incident, a banner under the page bar: "Failing now · part of an incident across 4 agents" linking to it. Below the occurrences, a small **Incidents** list of past incidents on this issue: period, calls failed, how it stopped, each linking to its page.

## Home

Add **Failing now** as the first tile when an incident is open, linking to Action items. Hidden when nothing is failing.

Placeholder agents: Insurance renewals, Restaurant reservations, Car service booking, Clinic after-hours, Dental reception. All numbers and names are placeholders.
