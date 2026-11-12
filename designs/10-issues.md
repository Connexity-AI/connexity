# Prompt for Claude Design: the Issues page and a single issue

Paste everything below the line into the existing Connexity project in Claude Design. It designs the Issues page from the sidebar, the page for one issue, and corrects how issues are counted elsewhere.

---

Design the **Issues** page and the page for **a single issue**, in dark and light, using the existing design system, sidebar, page bar and the fixed categories (prompt 06).

## What an issue is

An **issue** is one symptom on one agent, for example "Booking tool returned an error" on Car service booking. Each time it happens is an **occurrence**: one moment in one call, with the call and the time. An issue collects all its occurrences, whether 3 or 300, and it lives forever. Its size is the number of calls it affected (a call can hold more than one occurrence). The same symptom on three agents is three issues.

An issue is **Critical** when it fails the calls it appears on, otherwise a **Warning**. Its status is one of: **Open**, **Reopened** (it came back after a fix), **Resolved** in a version, or **Accepted as known**.

**Fix counts elsewhere to match:** the Home tiles and the roadmap count issues in this sense, and show calls affected next to them. A roadmap category reads "Transfers and escalation · 6 issues · 412 calls", not "42 issues".

## Screen: Issues

1. **Page bar:** "Issues", the period picker on the right.
2. **Number tiles:** Open 64, Critical 9, Reopened 3, Resolved 18 (in the period), Calls affected 212 of 1,284.
3. **Find:** one search field, then compact filters: Agent, Category, Severity, Status, Period. Same pattern as the Calls page.
4. **The list,** grouped by the fixed categories, each group collapsed to its name, issue count and calls affected. Inside a group, worst first: critical and reopened at the top, then by calls affected. One compact row per issue:
   - the title ("Booking tool returned an error")
   - the agent
   - Critical or Warning
   - calls affected ("38 calls · 3%")
   - status, with Reopened standing out
   - the roadmap milestone it belongs to ("Milestone 64")
   - last seen ("2 hours ago")
   Clicking a row opens the issue.

## Screen: a single issue

1. **Page bar:** the issue's title, the agent, Critical or Warning, and the status label ("Open", "Reopened", "Resolved in version 15", "Accepted as known").
2. **Number tiles:** Calls affected 38 of 1,120, First seen 2 Nov, Last seen 2 hours ago, Incidents 2, Milestone 64.
3. **Tip:** one short paragraph from Connexity: the likely cause and what to change. "The booking tool times out when the caller gives a date without a year. Send the year explicitly, or handle an empty result by offering to call back." Quietly styled, clearly from Connexity.
4. **The chain:** one horizontal line of steps showing where this issue is: **Found → In the spec → Tested → Fixed in a version → Confirmed on real calls.** Done steps are filled, the current one is marked, later ones are hollow. Each step links to its place: the rule on the agent's Spec tab, the test cases on the Tests tab, the version. When the behaviour is not in the spec yet, the second step reads "Waiting for a clarification" and links to it in Action items.
5. **Over time:** affected calls per day for the period, with version marks, so the start and the effect of a fix are visible.
6. **Occurrences:** the latest occurrences, newest first, one compact row each: the time, the call (caller "•••• 4821", duration, result), and the moment in the call ("at 1:42"). A quiet "All 41 occurrences on 38 calls" line opens the Calls page filtered to this issue. A row opens the single call at that moment.
7. **Incidents:** shown only for critical issues. One row per incident: period, calls failed, status, cause.
8. **History:** the decision records, newest first: status changes, who made them, when and why ("Accepted as known by Alex, 9 Nov · 'Caller hangs up during hold music, not the agent'").
9. **One action:** "Accept as known", a quiet button that asks for a reason. Only a person can confirm it; the assistant can propose it, which shows as an Action items card.

Read only otherwise. No "send to assistant": the assistant reaches every issue through MCP.

Placeholder agents: Insurance renewals, Restaurant reservations, Car service booking, Clinic after-hours, Dental reception. All numbers and names are placeholders.
