# Prompt for Claude Design: small adjustments across the app

Paste everything below the line into the existing Connexity project in Claude Design once the list is complete. Each item is a small change to screens already designed.

---

Apply these small adjustments across the whole app, in dark and light. Keep everything else as it is.

## 1. "Accept as known" becomes "Archive"

- Rename the issue status **Accepted as known** to **Archived** everywhere: the issue page, the Issues page filters and rows, tiles, history lines and Action items cards.
- The action on the issue page becomes **Archive**. It opens a small dialog: a required reason, and how long, **Until it gets worse** (the default: the issue comes back on its own when it starts happening much more often) or **Forever**.
- An archived issue leaves the open lists, Home counts and the roadmap, but its occurrences are still recorded. On the issue page it shows "Archived by Alex, 9 Nov · until it gets worse · 'Callers hang up during the carrier's hold music'".
- An archived issue **stops counting** against the agent's score, reliability and quality from the moment it is archived. The past is never rewritten: the agent's quality chart and the score history get a small mark on that date ("Issue archived by Alex"), so a jump in the number is always explained.
- Every archive is **recorded**: who archived it (a person, or the assistant with the person who approved it), when, the reason and the duration. The record shows on the issue page's history, as a mark on the charts, and in the Archived rows of the Issues page ("Archived by Alex, 9 Nov"). Unarchiving and an automatic return ("Came back: happening 3× more often") are recorded the same way.
- Only a person confirms archiving; when the assistant proposes it, it shows as an Action items card.
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
- **Spec tab with no spec yet:** a calm empty state, "No spec yet. Your assistant writes it from the agent's prompt; until then, checks that need a spec are paused for this agent." No button.
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
