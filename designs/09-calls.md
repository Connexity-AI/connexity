# Prompt for Claude Design: calls list and a single call

Paste everything below the line into the existing Connexity project in Claude Design. It adds a Calls page, a Calls tab on the agent profile, and the single call screen.

---

Add a way to browse and find calls, and the screen for a single call, in dark and light, using the existing design system, sidebar, page bar and tabs. People check the latest calls often and sometimes need one specific call ("a caller complained about this morning"). Keep it a quick glance, not an observability tool: no column pickers, query builders, saved views or exports, and nothing deeper than the single call.

## Sidebar and agent profile

- Add **Calls** to the sidebar after Agents: Home, Action items, Agents, Calls, Roadmap, Issues, Settings.
- Add a **Calls** tab to the agent profile, after Overview: Overview, Calls, Issues, Spec, Tests. It is the same list, already filtered to that agent, without the agent filter.

## Screen: Calls

1. **Page bar:** "Calls", the period picker on the right.
2. **Number tiles:** Calls 1,284, Failed 37, Degraded 212, Clean 1,035, for the period.
3. **Find:** one search field for a phone number or call ID, then compact filters: Agent, Result (Failed, Degraded, Clean), Category (the fixed categories from prompt 06), Period, Source (Real by default; Simulated and Test on request).
4. **The list,** newest first, one compact row per call:
   - time ("Today 09:42")
   - agent
   - caller as the last four digits only ("•••• 4821")
   - duration
   - result: Failed, Degraded or Clean. Colour only for Failed and Degraded; Clean stays quiet.
   - the worst finding in one plain line ("Transfer to the front desk dropped the call"), empty for clean calls
   - a small "Simulated" or "Test" label when the call is not real
   Clicking a row opens the single call.

## Screen: a single call

Opened from the calls list, an issue, an Action items card, or a test. Read only.

1. **Page bar:** the agent's name, date and time, duration, caller "•••• 4821", the result label (Failed, Degraded or Clean) and, when not a real call, a "Simulated" or "Test" label.
2. **For a simulated call,** one line under the page bar: the test case, the rule it proves and its result: "Proves: Never quote above the asking price · Failed".
3. **Recording:** a player across the full width with a waveform. Flagged moments are marks on the timeline, critical ones prominent, warnings quiet. Clicking a mark jumps the audio and the transcript to that moment.
4. **Findings:** a short list under the player, worst first. Each is one plain sentence, its category, and a link to the issue it belongs to. Clicking a finding jumps to its moment.
5. **Transcript:** turn by turn, Agent and Caller, following the audio (the playing turn is highlighted). A flagged turn carries its finding inline, at the place it happened. When a finding sits on a tool call, the transcript shows a single muted line at that point ("Tool call failed: booking"), with no arguments or results. A reply's delay is shown ("3.4 s") only where a Responsiveness finding flags it. When the call has a critical moment, it opens scrolled to that moment.

Not on screen: tool call arguments and results, workflow executions, CRM records, version details beyond "Version 14", latency charts. The assistant reads those through MCP.

Placeholder agents: Insurance renewals, Restaurant reservations, Car service booking, Clinic after-hours, Dental reception. All numbers, names and phone digits are placeholders.
