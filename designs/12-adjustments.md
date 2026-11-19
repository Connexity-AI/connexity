# Prompt for Claude Design: small adjustments across the app

Paste everything below the line into the existing Connexity project in Claude Design once the list is complete. Each item is a small change to screens already designed.

---

Apply these small adjustments across the whole app, in dark and light. Keep everything else as it is.

## 1. "Accept as known" becomes "Archive"

- Rename the issue status **Accepted as known** to **Archived** everywhere: the issue page, the Issues page filters and rows, tiles, history lines and Action items cards.
- The action on the issue page becomes **Archive**. It opens a small dialog: a required reason, and how long, **Until it spikes** (the default) or **Forever** (see item 28).
- An archived issue leaves the open lists, Home counts and the roadmap. On the issue page it shows "Archived by Alex, 9 Nov · until it spikes · 'Callers hang up during the carrier's hold music'".
- **While an issue is archived, it is hidden everywhere, on every call, including calls from before it was archived** (replaces "from the moment it is archived; the past is never rewritten"):
  - it does not appear on calls: no finding on the single call, never a call's worst finding;
  - it does not make calls fail or degrade, so a call with only this issue reads Clean;
  - it does not count against the agent's score, reliability or quality;
  - the assistant does not see it on calls either.
- **It is still found and stored behind the scenes.** When it is unarchived, by a person, by the assistant with a person's approval, or by a spike, every call it hit counts again, including those from while it was archived. The quality chart and the score history get a small mark on each archive and unarchive date ("Issue archived by Alex"), so a jump in the number is always explained.
- Every archive is **recorded**: who archived it (a person, or the assistant with the person who approved it), when, the reason and the duration. The record shows on the issue page's history, as a mark on the charts, and in the Archived rows of the Issues page ("Archived by Alex, 9 Nov"). Unarchiving and an automatic return ("Came back: it spiked") are recorded the same way.
- Only a person confirms archiving, on the issue page or by approving it when their assistant asks (item 28).
- The Issues page status filter reads: Open, Reopened, Resolved, Archived.

## 2. Incident page: a lighter blast radius chart

The chart reads as a wall of pink blocks. Change it:

- **Finer, thinner bars.** Use 5-minute buckets instead of 15 (about 24 bars for 2 hours instead of 9). Bars are narrow with clear gaps between them, never wide blocks.
- **Less colour.** The bars use the severity colour at reduced strength; only the latest bar (now) is full strength. The "Calls failed" tile keeps its number in the severity colour but its label goes back to the normal muted label colour.
- **Remove the per-agent rows from the chart.** The four thin strips are too small to read and waste the left third of the card on labels. The chart shows all agents together, full width, with a light y-axis (0 and the maximum, e.g. "6") so the bars have a scale.
- **Per agent goes into the Agents and issues list** below: each agent row gets a small sparkline of its failed calls over the same period, next to its count and "Still failing" or "Stopped at 10:05".
- **No duplicated period.** Drop the Period tile; the page bar already says "Started today 09:12 · 2 h". The tiles become Agents, Calls failed, Callers, Time to detect (and Time to close once closed).
- Lower the chart's height by about a third.

## 3. Action items: incidents get their own tab

Replace the "Now" tier from the incidents prompt. Action items gets two tabs under the page bar: **Incidents** and **To do** (clarifications, archive proposals, versions live without passing their tests, everything else that needs input).

- **Opens on Incidents** when an incident is open, otherwise on To do. Each tab label shows its count: "Incidents 2", "To do 14".
- **A glimmering exclamation mark** while any incident is open: a small exclamation icon in the severity colour with a slow, soft glow (fading between about 60% and 100% over 2 seconds; no blinking, no movement). It sits on the Incidents tab label, on the Action items entry in the sidebar, and on Home's Failing now tile. With reduced motion turned on it stays still. It disappears when no incident is open.
- **Each tab has its own tiles.** Incidents: Open 2, Calls failed 37, Agents 5, Closed this week 3. To do: Open 14, Critical 4, Answered this week 9, Parked 31. Remove the Failing now tile from Action items.
- **Incidents tab:** open incidents first, closed ones in a collapsed "Closed" section below. Make the cards compact and drop the repetition:
  - one status label only ("Failing now" or "Stopped at 10:41"); remove the "Incident" word in the top right and the "Incident ·" prefix in the title, since the tab already says it
  - the title, then one muted line: agents, calls failed, since when, what changed just before
  - **a small chart on the right of the card:** failed calls across the whole fleet over the incident's period, thin bars in the muted severity colour, latest bar at full strength, no axes or labels. At a glance it shows whether the incident is growing or fading.
  - **the whole card is clickable** and opens the incident, with a subtle hover state. Remove the "Open incident" button entirely.
  - one way to close: when the assistant has proposed closing, show only its proposal with "Confirm and close" and "Reject"; otherwise a single quiet "Close" button. Clicking these does not open the incident.

## 4. "Active incidents" instead of "Failing now"

Replace the phrase "Failing now" everywhere:

- An incident is **Active** or **Closed** (instead of Open or Closed), in labels, filters, tiles and the incident page's page bar.
- Home's tile becomes **Active incidents 1**, with the glimmering exclamation mark.
- The Issues page section above the categories becomes **Active incidents**.
- The issue page banner reads "Part of an active incident across 4 agents".
- The Incidents tab's first tile reads **Active 2**.
- On an incident card, the label says how the active incident is doing: **Still failing** or **Stopped at 10:41** (failures have stopped but nobody has closed it yet).

## 5. Incidents get their own page

Move incidents out of Action items onto their own page.

- **Sidebar:** Home, **Incidents**, Action items, Agents, Calls, Roadmap, Issues, Settings. Incidents shows the number of active incidents next to its name.
- **Remove the tabs from Action items.** It goes back to one list of everything that needs input (clarifications, archive proposals, versions live without passing their tests), with its tiles Open, Critical, Answered this week, Parked. No incidents on it, and no exclamation mark on its sidebar entry.
- **The glimmering exclamation mark** moves to the Incidents entry in the sidebar, and stays on Home's Active incidents tile, which now links to the Incidents page.

## 6. Screen: Incidents

Everything the Incidents tab had, as its own page:

1. **Page bar:** "Incidents", the period picker on the right. No subtitle.
2. **Number tiles:** Active 2, Calls failed 37, Agents 5, Closed 3 (in the period), Time to close 1 h 40 (median).
3. **Active incidents** as the same compact cards (status label, title, one muted line, whole card clickable, one way to close), then the collapsed **Closed** section.

## 7. Every small chart says its time scale

The small charts on the incident cards are unreadable: nobody can tell whether the bars are minutes, hours or days. Fix them, and apply the same rule to every small chart without axes in the app (sparklines included):

- Under the chart, two small muted labels at its ends: the start and the end of its span ("09:12" … "Now", or "6 Nov" … "Today").
- In its top right corner, the peak value with its unit ("6 per 5 min").
- Bars of equal width with equal gaps; a period with no failures is a thin baseline, not a missing bar.
- A small chart with no visible time scale is not allowed.

## 8. Remove Active incidents from the Issues page

Remove the **Active incidents** section above the category groups on the Issues page. Incidents already have their own page in the sidebar and a tile on Home. The Issues page starts with its tiles and goes straight to the issues. The banner on a single issue page ("Part of an active incident across 4 agents") stays, since it links that issue to its incident.

## 9. Remove Active incidents from Home

Remove the **Active incidents** tile from Home. The Incidents entry in the sidebar, with its count and glimmering exclamation mark, is the only place that signals an active incident. Home's tiles become Agents, Calls, Latency, Issues, Critical, Warnings, Clarifications. This replaces what items 4 and 5 said about Home's tile.

## 10. Remove incidents from the Roadmap

Remove everything about incidents from the Roadmap page: tiles, labels, markers and any incident rows or links. The roadmap is about planned improvement; incidents live on their own page.

## 11. Readiness: a second number, loud only while incomplete

Besides the fleet score (quality, which only fixes move and which never stops moving), the app has a second number: **Readiness**, how complete the team's setup is. It is meant to reach 100% as fast as possible, mostly driven by the AI assistant during onboarding, and then stay quiet. Readiness never changes the score.

Readiness is made of six controls, fleet-wide and per agent:
- Alerts go to Slack or another messenger
- An incident channel the assistant watches
- Every agent has a spec
- Every agent's backends are connected (the n8n workflows and CRM behind its tools), so issues can be traced into the systems it touches
- Tests cover at least 80% of each agent's spec rules
- The deployment gate is on for every agent

**Where it shows, only while below 100%:**
- **Sidebar, bottom profile area:** a small ring with "Readiness 60%". Clicking it opens the Readiness stage of the Roadmap.
- **A thin stripe across the top of the app,** above the page bar on every page: "Readiness 60% · 2 steps left: connect alerts to Slack, turn on the deployment gate. Your assistant can finish this." Calm, neutral colour (not severity colour), one line, with a small close icon that hides it for the day.
- When Readiness reaches 100%, the ring and the stripe disappear. They come back when it drops (a new agent synced without a spec or tests, Slack disconnected, coverage falling under 80% after new rules), naming what is missing: "Readiness 92% · Dental reception has no tests".
- Home does not show Readiness.

## 12. Roadmap: Readiness first, then milestones

The Roadmap becomes one path in two stages:

1. **Readiness** at the top, while below 100%: a progress bar to 100% and the list of controls, each done, in progress or not started, with a number where it has one ("Test coverage 62% → 80%", "Spec 4 of 5 agents", "Backends 3 of 5 agents"). Per-agent controls expand to show which agents are missing it. No points, no dates from the pace.
2. **Milestones** below it, unchanged: the quality path to 99.

When Readiness is at 100%, the stage collapses into one quiet line at the top, "Readiness complete", expandable.

## 13. An agent can be without a spec until the assistant writes it

The spec is no longer created automatically when an agent connects; the AI assistant writes it, guided by Connexity, as a Readiness step.

- Change any copy that says the spec is inferred on connection or that no agent is ever without one.
- **Spec tab with no spec yet:** a calm empty state, "No spec yet. Your assistant writes it from the agent's prompt." No button. (Until a check needs a spec, the build leaves out "until then, checks that need a spec are paused for this agent"; Dmytro, 2026-11-15.)
- **Agents list and agent profile:** an agent without a spec shows a small muted "No spec" label next to its name.
- Clarifications only appear for agents that have a spec.

## 14. Incidents page: automatic incident response

Some incident actions can be switched on to run without a person, so the assistant can act at 3 a.m. Connexity predefines which actions are allowed; a team can only switch those on. Today there are two.

- **A quiet line under the Incidents tiles:** "Automatic response: roll back on 3 of 5 agents · merge and split off". Clicking it opens a small panel (no tabs, no new page).
- **The panel:** one row per allowed action:
  - **Roll back:** "Roll the agent back to the last version that passed its tests, then tell you."
  - **Merge and split:** "Correct how failures are grouped into incidents."
  Each row has a control with three choices, **Off**, **All agents**, **Some agents** (a checklist of agents), and a muted line with who switched it on and when ("Alex, 10 Nov") and how often it was used ("Used twice this month").
- Only a person switches an action on. When the assistant proposes it, it shows as an Action items card to confirm. Every change is recorded: who, when, old and new value.
- **Under the rows, a collapsed log, "Taken automatically":** "03:12 · Rolled back Car service booking to version 14 · rule switched on by Alex, 10 Nov", each linking to its incident.
- **In an incident's timeline,** an automatic action reads "Rolled back automatically at 03:12 · rule switched on by Alex, 10 Nov".

## 15. Incidents page: make automatic response visible

The one-line "Automatic response" summary under the tiles is almost invisible. Replace it with a compact card between the tiles and the incident cards, always open:

- **Card header:** "Automatic response" with the rotate icon, and on the right a quiet link "Taken automatically · 2 this month" that opens the log.
- **Two rows, controls visible without expanding:**
  - **Roll back** · "Roll the agent back to the last version that passed its tests, then tell you." · a segmented control **Off / All agents / Some agents** (Some agents shows "3 of 5" and opens the agent checklist) · muted "Alex, 10 Nov".
  - **Merge and split** · "Correct how failures are grouped into incidents." · the same control · muted "Off".
- **When both are off,** the card shows one plain line under its header: "Incidents wait for a person, even at night." Neutral colour, no warning styling.
- Keep the card short (about the height of a tile) and in the normal surface colour; it is a setting, not an alert, so no severity colour.

## 16. Readiness: add automatic rollback

Add a seventh control to Readiness: **Automatic rollback is on** (per agent). It counts as done for an agent when "Roll back" in the Incidents page's automatic response covers that agent. On the Roadmap's Readiness stage it reads "Automatic rollback 3 of 5 agents" and expands to the agents without it; in the Readiness stripe it reads, for example, "turn on automatic rollback for 2 agents". Clicking it opens the automatic response card on the Incidents page.

## 17. Remove "Merge and split" from automatic response

Grouping failures into incidents is done by Connexity itself, so it is not an automatic response setting. Remove the **Merge and split** row from the automatic response card on the Incidents page; the card keeps only **Roll back**. Remove "merge and split off" from any summary text.

When Connexity groups wrongly, a person or the assistant corrects it. Keep **Merge** and **Split** as quiet items in the incident page's "…" menu: Merge asks which active or recent incident to merge with; Split shows the incident's agents and issues as a checklist to move into a new incident. Every correction is recorded and shows in the timeline: "Merged with 'Quote lookup timing out' by your assistant, 10:20".

## 18. Playbook: its own tab on the Incidents page

Replace the automatic response card (items 15 and 17) with a second tab on the Incidents page: **Incidents** and **Playbook**. The Incidents tab is the page as it is now, without the card.

The Playbook tab holds **instructions saved for the team's AI assistant**: what it may do when an incident opens, and whether it must ask first. Connexity never acts itself; it stores the rules, and the assistant reads them.

### How it works (explainer at the top of the tab)

A short, calm explainer in four numbered steps, one line each, readable in five seconds. It is **collapsible**: a single line "How the playbook works" with a chevron; open by default only until the first rule is switched on, collapsed after that, and it remembers the person's choice.

1. Connexity opens an incident and sends an alert to your Slack (or other messenger).
2. If your AI assistant is connected to that channel, it picks the alert up.
3. It checks these rules in Connexity.
4. It acts: either it asks you for approval in its session, or, where you ticked "Approve automatically", it goes ahead on its own (for example at 3 a.m.).

When the assistant is not connected to an alert channel yet, a plain line under the steps says so: "Your assistant isn't connected to an alert channel yet, so these rules won't run", linking to Readiness. Neutral colour, no warning styling.

### The rules

One row per action, each with:
- the action name and one plain line on what the assistant does
- **Allowed for:** Off / All agents / Some agents (a checklist)
- a checkbox **Approve automatically**, with a muted hint "No one has to approve it in the moment, for example at 3 a.m." When unchecked, the assistant asks a person in its session before acting.

Two actions for now:
- **Roll back:** "Roll the agent back to the last version that passed its tests."
- **Hotfix:** "Write a fix and deploy it once it passes its tests in Connexity." A hotfix always passes its tests before it deploys, even when approved automatically; say this in its line.

Under the rules, the collapsed **Taken automatically** log stays, now showing for each entry whether a person approved it in the session or it was approved automatically: "03:12 · Rolled back Car service booking to version 14 · approved automatically".

Only a person changes these rules; when the assistant proposes a change, it shows as an Action items card. Every change is recorded.

No small metadata lines on the rules (who changed it, when, how often it was used): they are noise. Changes are still recorded and visible in the log.

## 19. Onboarding is the start of Readiness

There is no separate onboarding flow or wizard. Readiness becomes one list of eleven steps in two parts, and onboarding is simply its first part.

**Getting started** (new):
1. Assistant connected
2. Voice platform connected (Retell)
3. Agents and calls synced ("640 of 1,284 calls", with a thin progress bar while syncing)
4. First scan done

**Controls** (the existing seven): alerts to Slack, an incident channel the assistant watches, a spec for each agent, backends connected, tests covering 80% of spec rules, the deployment gate, automatic rollback.

The percentage counts all eleven steps.

**Before the first scan is done, Readiness is the whole screen.** There is nothing else to show yet, so after sign-up the app opens straight onto the Readiness list (sidebar visible, other pages empty). The Getting started steps tick live as the assistant works; the step in progress shows a small spinner and one plain line ("Your assistant is syncing calls"). Under the list, one calm line: "Your assistant is doing this. You can close this page."

- **If no assistant is connected yet,** step 1 expands to show how to connect one: a short copyable snippet for Claude Code, and a quiet link for other assistants. This is the only place in the whole app with a setup instruction for the person.
- **When the first scan finishes,** step 4 ticks with its result in one line, "64 issues across 5 agents · 9 critical", and a single button appears: **Open Home**. From then on, the app opens on Home.

**After the first scan,** Readiness shrinks to the stripe at the top and the ring in the sidebar (item 11), and the Roadmap's Readiness stage lists all eleven steps (Getting started already done). Home needs no special first-visit banner: its tiles are the scan's result.

## 20. Settings

Design the Settings page, in dark and light. Settings is mostly for seeing how things are set up; a person changes something only where the decision must be theirs. No setup forms: the AI assistant makes connections through MCP. No small metadata lines.

**Layout:** a short list of sections on the left inside the page, the selected section on the right: **Connections, Checks, Gate, Team, Audit log, Usage.**

### Connections (read only)
- One row per connection: the assistant, Retell, each backend (n8n, the CRM), Slack or another alert channel. Each row: name and status, **Connected**, or **Failing** in the severity colour with one line saying what fails ("n8n: last 12 executions failed to load").
- A calm tip at the top of the section: "To add or change a connection, ask your assistant, for example: 'Connect our n8n to Connexity.'" The example is in a copyable, monospace style.
- The only action is **Disconnect** on a row (a person's security decision, which must work even if the assistant is the problem). It asks for confirmation.

### Checks (a person decides)
- The check library as a list: name, what it catches in one line, and its setting, **Off / Flags / Fails the call**, for the whole fleet. Expanding a check lets the person set it differently for chosen agents.
- The check's measured precision next to the setting, as advice ("Right 96% of the time").
- A change asks for a reason and becomes a decision record. A change proposed by the assistant shows as an Action items card.

### Gate (a person decides)
- What the gate runs before a version may ship: which test levels (Text, Audio, Phone), the passing threshold, and how many repeats count as flaky. Pre-filled with Connexity's default, with a quiet "Reset to default".

### Team
- The people in the workspace and whether each can approve (archive, close incidents, override the gate, change the Playbook and checks).
- **Invite** by email, a small form: this is a person's own action.

### Audit log
- Every decision record across the fleet, newest first, one line each: "10 Nov · Alex archived 'Callers hang up during hold music' · 'Carrier hold music, not the agent'". Covers archives, incident closes and merges, gate overrides, Playbook changes, check settings, disconnections.
- Compact filters: agent, person or assistant, kind of decision, period.

### Usage
- Call minutes observed and simulation minutes this month, each as a number against the plan with a thin bar. Pricing is by usage only.

## 21. Settings › Connections: grouped, with suggestions

The flat list is hard to read. Group it and suggest what is missing.

- **Groups, in this order, each with a small heading:** Assistant, Voice platform, Backends, CRM, Alerts. A group with nothing connected and nothing suggested is hidden.
- **Connected rows** stay as they are: name, status (Connected, or Failing with its one line), Disconnect. Drop the "· Assistant", "· Voice platform" suffixes; the group heading says it.
- **Suggested rows** sit at the end of their group, muted, for what Connexity sees is missing:
  - from Readiness, e.g. under Alerts: **Slack** · "Get incident alerts where your assistant can pick them up"
  - from what the agents actually call, e.g. under Backends: **Make** · "Your agents call 3 Make webhooks that Connexity can't see yet"
  Each suggested row has, instead of a status, the exact request for the assistant in the copyable monospace style with Copy: "Connect our Slack to Connexity for incident alerts."
- **A failing row** gets the same kind of copyable request under its error line: "Fix the n8n connection in Connexity."
- **Remove the generic tip card at the top;** the requests on the suggested and failing rows replace it.

## 22. Settings › Billing (replaces Usage)

Rename the **Usage** section to **Billing**. Pricing is by usage only, paid in **credits**: a limited Free plan, and a Paid plan where the team tops up credits. No small metadata lines.

1. **Plan:** "Free" or "Paid", with one plain line on what it includes, and on Free a quiet "Upgrade".
2. **Credits:** the balance as one large number ("8,420 credits"), a thin bar of this month's use split by what used it (calls observed, simulations, judge checks), and one line: "Lasts about 3 weeks at your current rate".
3. **Top up:** three fixed amounts as buttons (for example 5,000, 20,000, 50,000 credits with their price), and an **Auto top-up** switch with its rule: "When the balance falls below 1,000, add 5,000".
4. **Pricing:** a small table of what each thing costs in credits: 1 minute of call observed, 1 minute of text simulation, 1 minute of audio simulation, 1 real phone test call, judge checks ("free with your own model key").
5. **Free plan limits** (placeholders): 1,000 call minutes observed a month, text simulations only (audio and phone on Paid), 30 days of history. On Free, the plan area shows the allowance used this month.
6. **Invoices:** a compact list (month, amount, download).
7. **Payment method:** the card on file ("Visa ending 4242") with **Change**, which opens the payment provider's own page. No card fields in Connexity.

**When credits run out:** recording calls, rule checks, incidents and alerts keep running, so nothing goes unnoticed. Simulations and paid judge checks pause. A thin stripe at the top of the app (same style as the Readiness stripe) says: "Out of credits: tests are paused. Top up or turn on auto top-up", linking to Billing.

**Low balance:** when credits will last less than about a week, the sidebar's profile area shows a small line under the Readiness ring: "Credits low · 3 days left", linking to Billing. Hidden otherwise.

## 23. Personal settings

Personal settings belong to the person, not the workspace, so they live behind the profile area at the bottom of the sidebar, not in Settings.

**Profile menu:** clicking the person's avatar and name in the sidebar's profile area opens a small menu: **Account**, **Theme** (Dark, Light, System, inline), and **Sign out** at the bottom, separated by a divider.

**Account page** (same layout as Settings, its own short section list on the left):

1. **Profile:** name, email (shown, changed through a confirmation email), avatar from initials. Save button appears only after a change.
2. **Sign-in and security:**
   - **Password:** "Change password" opens a small form (current, new, confirm).
   - **Sign-in methods:** email and password, Google, each Connected or "Connect".
   - **Two-step verification:** On or Off, with "Set up".
   - **Sessions:** where the person is signed in, one line each ("Chrome on Mac · Kyiv · now"), with "Sign out" per session and "Sign out everywhere else".
3. **Assistant access:** the AI assistants this person has connected with their account (they act as this person), each with **Revoke**. A short line: "Anything your assistant does is recorded as done by your assistant on your behalf."
4. **Notifications:** what emails this person gets, as switches: weekly report, incident alerts, clarifications waiting for me, billing. One switch each, no extra lines.
5. **Delete account:** at the very bottom, a quiet danger action that asks to type the email to confirm. If the person is the workspace's only member who can approve, it explains that someone else must be able to approve first.

## 24. Workspaces per client, and a thin agency account

Agencies run agents for many clients. Each client is its own **workspace**; everything designed so far (Home, Incidents, Action items, Agents, Calls, Roadmap, Issues, Settings, Readiness, Playbook) belongs to one workspace and stays exactly as it is. Clients never log in.

- **Workspace picker inside the profile menu,** to keep the sidebar light. The Connexity logo stays at the top unchanged (no white-labelling), and nothing new is added to the sidebar. The profile area at the bottom shows the person's name with the current workspace's name under it in muted text ("Bright Dental"), so it is always clear which client you are looking at. Clicking the profile opens the menu (item 23) with a **Workspaces** part at the top: the workspaces this person can access, the current one ticked, a search field when there are more than eight, **New workspace**, and **Agency settings**; then a divider, and the existing Account, Theme and Sign out.
- **Agency settings** (the agency account above the workspaces, same layout as Settings) has two sections:
  - **Members:** everyone in the agency, and for each person which workspaces they can access (All, or chosen ones) and whether they can approve. Invite by email.
  - **Billing:** item 22 moves here from workspace Settings. One credit balance for the whole agency, one set of invoices and one card. The credits bar and the usage are broken down **per workspace** ("Bright Dental 3,120 credits this month"), so the agency can bill each client.
- **Workspace Settings** loses Billing and Usage; Team shows only the members with access to this workspace and links to Agency settings to change access.
- **Assistant access is per person** (Account › Assistant access, item 23): each person connects as many assistants as they like. An assistant reaches exactly the workspaces its person can access. Under each connected assistant, one muted line: "Reaches 4 workspaces". In workspace Settings › Connections, the Assistant group lists the assistants that can reach this workspace and whose they are ("Claude Code · Dmytro").
- Not now: a superview across all workspaces (later), client logins.

## 25. Single call: tool calls inline in the transcript

The single call screen shows tool calls, not only findings on them. This replaces the earlier rule that tool calls stay off screen.

- **Every tool call appears in the transcript at the moment it happened,** as one compact, muted line between the turns: a small tool icon, the tool's name, its status and duration ("booking · ok · 820 ms"; a failed one reads "booking · failed · 3.1 s" in the severity colour).
- **Collapsed by default.** Clicking the line expands it in place to show the **arguments** and the **result**, each as formatted, monospace key-value text (long values wrap; very long ones show the first lines with "Show all"). Secrets are already masked by the backend; show them as "••••".
- **When the tool ran an n8n workflow,** the expanded block ends with one quiet line, "Workflow: quote-lookup v7 · 9 steps", without opening the workflow's steps on screen.
- The recording's timeline gets a small tick for each tool call, so clicking a tick jumps the audio and the transcript to it.
- Nothing else changes: findings still show inline, and the screen stays read only.

## 26. Readiness step 1: connect Claude Code with a setup prompt

This replaces the single Claude Code snippet from item 19; everything else on the screen stays as it is.

While no assistant is connected, step 1 "Assistant connected" is expanded and shows two small tabs inside the step, under the step's name: **Claude Code** (selected by default) and **Claude.ai or ChatGPT**. Keep them quiet: text tabs with a thin underline on the selected one, not buttons.

- **Claude Code tab:**
  - One line: "Paste this into Claude Code, in the app or the terminal."
  - A primary button: **Copy setup prompt**. The prompt itself is never shown on screen, because it contains a personal token.
  - Under the button, one muted line: "Creates a personal access token for you. You can revoke it in Account." The word "Account" links to the Account page, Assistant access section.
  - After a click, the button reads "Copied" for about two seconds, then goes back to "Copy setup prompt".
  - If the prompt cannot be created, the muted line is replaced by: "Could not create the setup prompt. Try again."
- **Claude.ai or ChatGPT tab:**
  - One line: "Settings → Connectors → Add custom connector".
  - The address `https://mcp.connexity.ai/mcp` in a monospace field, with a small **Copy** button at its right end (the same field and button style the current snippet uses).
  - One line under it: "then click Connect and sign in."
- **When the assistant first connects,** the step ticks on its own, with no reload: the tabs collapse, the check mark appears, and the step's detail on the right reads "Connected: Claude Code" (or the assistant's name, for example "Connected: ChatGPT"). Show this connected state as a second variant of the screen.

Keep the calm tone of the screen: no illustrations, no extra explanation, no other setup instructions anywhere else.

## 27. Issue page and Calls page: affected calls, not occurrences

Everything about an issue is counted in calls. The word "occurrence" leaves the screen.

**On the issue page:**

- **The Occurrences section becomes Affected calls**, "Latest first", with one row per call. A call where the issue happened twice is still one row.
- **Columns:** Time, Caller, Duration, Result, Moment.
  - **Moment** shows the first time it happened in that call ("at 2:01").
  - When it happened more than once, a quiet "· 2 times" follows ("at 2:01 · 2 times").
- **Clicking a row** opens the single call at that first moment.
- **The link under the list** reads "All 38 calls" instead of "All 41 occurrences on 38 calls", and opens the Calls page filtered to this issue.

**On the Calls page, when it is opened from an issue:**

- **The filter row** shows one extra chip before the other filters: the issue's title ("Booking tool returned an error") with a small ×. Clicking × removes it and shows every call again.
  - The chip only appears when the page is opened from an issue. It is not a dropdown, and the other filters stay as they are.
- **The tiles and the list** show only calls this issue affected. Search, the other filters and the period still work on top of it.
- **The last column** reads **Moment** instead of Worst finding, with the same "at 2:01 · 2 times" as on the issue page. A row opens the call at that moment.
- **The empty state:** "No calls match" with "Clear the search and filters" keeps the issue chip and clears only the others.

## 28. Archive: "Until it spikes", and archiving through the assistant

This replaces "Until it gets worse" from item 1. Everything else in item 1 stays.

**The Archive dialog on the issue page:**

- **The reason** stays required, as it is now.
- **"How long"** offers two options:
  - **Until it spikes** (the default): "Comes back if it starts happening twice as often as now."
  - **Forever**: "Stays archived until someone unarchives it."
- **The line under the buttons** reads only "Only a person can confirm this, here or through your assistant." Remove the sentence about proposals showing up in Action items.

**The archived line in the page bar:**

- **Archived by a person:** "Archived by Alex, 9 Nov · until it spikes · 'Callers hang up during the carrier's hold music'".
- **Archived through the assistant:** "Archived by your assistant, approved by Dmytro, 9 Nov · until it spikes · '…'".
- **Forever** reads "· forever" in place of "· until it spikes".

**When an archived issue spikes:**

- **It becomes Reopened** (the same dark Reopened label as everywhere else) and returns to the Issues page's Open list.
- **History gets a line,** decided by Connexity: "Came back: it spiked · 8 calls this week, twice as often as when it was archived".
- **The chart's "Archived by …" mark** stays where it was, and a second mark "Spiked" appears on the day it came back.

**Hidden while archived:** item 1 says how. When the issue comes back, its calls from the archived period show it again.

**Unarchiving** has no button on screen. When it happens through the assistant, history reads "Unarchived by your assistant, approved by Dmytro, 12 Nov · 'reason'".

Keep the word "spike" for this only. Never use "escalation" for an issue getting worse, because it means handing a call to a person ("Transfers and escalation").

## 29. Spec tab: critical rules

Every spec rule is now Critical or not. A failed critical rule fails the agent version in
testing; a failed rule that is not critical is a Warning. The assistant marks rules; the
person reads the mark here and asks the assistant to change it. Nothing on this tab marks
or unmarks a rule.

**On each rule:**

- **A "Critical" label** on a critical rule, the same red badge as the Critical severity
  on the Issues tab's rows (octagon icon and "Critical"). It sits before the rule's text,
  where the issue rows put theirs.
- **Rules that are not critical** have no label. Do not show "Warning" on them: it is
  only what a failure of them is called in test results.
- **The other marks stay as they are:** the money, safety or compliance tag, "From the
  prompt" or "Answered by …", and "In conflict".

**On each group's header:**

- **"2 critical"** beside the rule count, in the same small red badge as the Issues
  tab's group headers. No badge when the group has none.

**In the versions list:**

- **A version that only changed marks** reads "Critical rules marked by Alex's Claude
  Code · 17 Nov", beside "Written by …", "Copied to version 15" and "Answers added".
  Comparing it with the version before shows every rule kept.

**The order of rules** stays as it is: critical rules are not moved to the top.


## 30. Single call: a simulated call's rules and verdicts

A simulated call is a conversation the assistant ran against the agent before release: a
simulated caller talked to the agent in text, in a scenario. A judge then gave each
spec rule the scenario lists one verdict: Passed, Failed or Didn't come up. A scenario
lists several rules, not one, so "Proves: Never quote above the asking price · Failed"
becomes a line of rules. The person opens such a call from a link the assistant gives
them; it opens on the same single-call screen as a real call.

**The page bar:**

- **A "Simulated" label** beside the result label, as the design already has.
- **The version it tested,** "Version 15", and "Edited" when the draft was edited since
  it was published.
- **The result label** is the call's own:
  - Failed when a critical rule failed or a critical finding was raised;
  - Degraded when only other rules failed or only warnings were raised;
  - Clean otherwise.
- **No caller number and no duration:** a simulated call has neither.

**Under the page bar, one line: the scenario and the rules it was judged on.**

- **The scenario's name** first, muted: "Scenario: Price pushback".
- **Then each rule** as a compact chip: the rule in plain words, cut to one line, and
  its verdict:
  - Failed in red, with the Critical badge when the rule is critical;
  - Passed in green;
  - Didn't come up muted.
- **Failed rules come first.**
- **Clicking a chip opens its reason** under the line: one or two sentences from the
  judge, and the turns it rests on. Clicking a turn number scrolls the transcript to
  that turn.
- **When the line is longer than the width,** it wraps; there are rarely more than five
  rules.

**The rest of the screen:**

- **No player:** a text run has no recording. The findings list moves up under the
  rules line.
- **Findings and the transcript** are as on any call, with tool calls inline.
- **No times:** a text run has no timing, so no "0:42" stamps and no reply delays.
- **When the conversation stopped** because the platform failed or the call ran out of
  time, a muted line ends the transcript: "The conversation stopped: Retell did not
  answer". Such a call has no verdicts, and the rules line says "Not judged".

Placeholder rules: "Never quote a price above the price list", "Ask for the date of
birth before booking", "Offer the earliest slot first".

## 31. Agent Profile: the Tests tab, cut down for the demo

The Tests tab still shows the 1.x picture: test cases that each pass or fail, Text,
Audio and Phone levels, a version history with overrides, and a "Run tests" button.
Testing works differently now, and the demo shows only what is built.

**How it works now:**

- **The assistant writes scenarios.** A scenario is the stage for a simulated call: who
  calls, their goal, how they behave. Each scenario lists the spec rules it should
  bring up.
- **The assistant runs them** through MCP: a named set, a pick, or all of them. Each
  scenario repeats a few times, in text only for now.
- **After each simulated call, a judge gives every listed rule a verdict:** Passed,
  Failed or Didn't come up. Code checks also run on the call.
- **The version's verdict:**
  - **Failed** when a critical rule failed, when a critical code check found something,
    or when too many other rules failed;
  - **Verified** otherwise, with warnings;
  - **Not tested** until a run completes.

Rework the Tests tab for this. Read only: no Run button, no editing. The assistant does
both.

**The tab label:** "Tests 86%", the share of the spec's rules the runs checked.

**Number tiles across the top,** each with its base:

- **The verdict:** "Version 15 · Failed" in red, "Version 15 · Verified" or "Not tested",
  with "Edited" after the number when the draft was changed under the same number, and
  "tested today, 9:40" under it.
- **Coverage:** "86%" with "114 of 132 rules".
- **Scenarios:** "38" with "in 3 sets".
- **Flaky:** "2 rules": rules that both passed and failed.
- **Warnings:** "3": rules that are not critical that failed, and code checks that only
  flag.

**Why it failed:** the first section, shown only when there is something in it.

- **Critical first:** failed critical rules (with the Critical badge) and code checks
  that fail calls. **Then warnings,** in a quieter style.
- **A rule row:** the rule in one plain sentence, its category, and "Failed in 2 of 5
  simulated calls" (the calls that judged it; Didn't come up is not counted). It is
  marked "Flaky" when it also passed.
- **A code check row:** its title ("Tool call failed"), "Found by a rule", and "Found
  in 2 of 40 simulated calls".
- **Opening a row** lists its simulated calls: the scenario's name, the repeat, and the
  verdict (Failed, Passed). Each links to the call, which opens on the single-call
  screen with its rules line (item 30).

**All rules:** a collapsed section, grouped by the fixed categories, each group with
its count. Each rule shows passed, failed and didn't come up as three small numbers,
with the Critical badge on critical rules.

**Not checked:** a collapsed section, grouped by category: the spec's rules no run
judged. Each says why: "No scenario" when no scenario lists it, or "Didn't come up" when
scenarios list it but never reached it. Critical rules come first in each group.

**Scenarios:** the last section.

- **The named sets first,** as small chips with their counts ("smoke · 6").
- **Then every scenario,** one row each: its name, the caller's goal in one muted line,
  "3 rules", and the sets it is in.
- No editing and no running.

**Empty states:** the tab always shows; each state says what the assistant does next.

- **No spec yet:** "No spec yet. The assistant writes the spec first; then it writes
  scenarios for the rules."
- **A spec but no scenarios:** "No scenarios yet. The assistant writes them, one or more
  for each critical rule." It shows the coverage tile at 0%.
- **Scenarios but no completed run:** "Not tested yet. The assistant runs the scenarios
  through MCP." The scenarios section still shows.

**Not on the tab any more:** the version list and overrides (they come with the gate),
the Text, Audio and Phone rows (text is the only level), "Run tests", and test cases.

Placeholder agents and numbers as before. Placeholder rules: "Never quote a price above
the price list", "Ask for the date of birth before booking", "Offer the earliest slot
first".

## 32. Agent Profile: the Tests tab reads one full run, and the Spec tab shows its results

Replaces item 31's tiles, "Why it failed" and "All rules" (Dmytro, 2026-11-19). Screens:
"Connexity Agent Profile" (`tab=tests`, `tab=spec`) and "Connexity Agent Tests states".

**How a version is judged now:**

- **Coverage is tests written:** the share of the spec's rules that at least one
  scenario lists.
- **A full run** runs every scenario. Runs of a set or a pick are on demand and never
  change the verdict.
- **The verdict comes from the live version's latest full run:**
  - **Verified:** every rule checked (Passed or Failed) and nothing critical found;
  - **Failed:** a critical rule failed or a critical code check found something;
  - **Partially tested:** nothing critical, but some rule didn't come up or has no
    scenario;
  - **Not verified:** no full run of this version yet, with "Version 88 was verified 19
    Nov" when an earlier one was.
- Non-critical failures never fail a version; they show in the run's Failed count.

**Tests tab:**

- **Four tiles:** the verdict ("Version 88 · Verified" in its colour, "Full run · 19 Nov,
  9:40" under it), Coverage ("86%", "114 of 132 rules have a scenario"), Checked ("41 of
  43", "rules judged in the full run", "—" without one), Scenarios ("38", "3 sets").
- **Runs:** one row per run of the live version, newest first, five shown and "Show all N
  runs". Columns: When, Run ("Full · 7 × 3", "Set smoke · 7 × 3", "Pick · 2 × 3"),
  Result, Passed, Failed, Didn't come up, Critical (rules, each counted once per run),
  Version, Who ("Alex's Claude Code").
  - A full run's Result is the verdict word in its colour; an on-demand run's is a muted
    Passed or Failed with "on demand".
  - "3 calls stopped" in muted text under the result when calls ended in an error.
  - A run in progress: "Running · 12 of 21 calls" with a thin bar.
  - "N runs on earlier versions" opens the earlier versions' runs, grouped by version.
  - No drill-in from a run.
- **No** "Why it failed", "All rules", Flaky or Warnings tiles: the Runs table shows it.
- Phone width: compact rows, the counts on a second line.

**Spec tab:**

- Each rule shows its result from that full run: Passed, Failed, Flaky, Didn't come up or
  No scenario. A category with failed rules shows "2 failed" in its header.
- Under the title: "Results from the full run of 19 Nov", or "No full run on version 88
  yet" and no marks.

**Wording:** a code check's finding reads "Found by a code check"; "rule" means spec
rules only.

## 33. Agent Profile: a version filter beside the period

Dmytro, 2026-11-19: "Period + version filter", and "Spec 5 · written for version 88".
Screens: "Connexity Agent Profile" (`version=87`), "Connexity Calls" (embedded in the
agent page), "Connexity Agent Tests states" (Version filter section) and "Connexity
Agents and Overview" (Overview with a version picked).

- **The filter** sits beside the period picker: "All versions", or "Version 88 · live".
  It lists every version of the agent that has a call, newest first, the live one
  marked. With a version picked, the period still applies.
- **Every tab follows it:**
  - **Overview:** the tiles count only that version's calls in the period. The charts
    dim the other days and shade the picked version's days.
  - **Calls:** a Version column (on the agent page only) and only that version's calls.
  - **Spec:** the spec in force for that version, the newest written for it or an
    earlier one; "No spec was written for version 87 or earlier" when none.
  - **Tests:** that version's verdict, tiles and runs.
- **The Spec title** reads "Spec 5 · written for version 88".

## 34. Agents list and agent Overview: latency as p50/p95, the list's versions

Dmytro, 2026-11-19 (roadmap 10.199), from design review (18). Screens: "Connexity
Agents", "Connexity Agent Profile" (Overview), "Connexity Home" and "Connexity Agents and
Overview".

- **One measure of latency everywhere:** p50 and p95 over every reply in the period,
  shown "1.6s/3.1s", p50 large and p95 muted after it, labelled "Latency p50/p95". The
  Dashboard tile changes to the same order.
- **The Agents list:** a Version column, "v14", with "Since 6 Nov" on hover; the latency
  column "Latency p50/p95". The header loses "Retell · synced 5 minutes ago".
- **The agent's Overview:** the latency tile as above; the chart is one line of daily
  p50, "Latency p50", with the version marks ("New version") and, with a version picked,
  that version's days shaded. No goal line, no warning colour on latency.
