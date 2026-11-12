# Prompt for Claude Design: Connexity web app

Paste everything below the line into Claude Design. Attach the logo PNG (the orange three-loop mark) with it.

---

Design the web app for **Connexity**, in dark and light. Start with a small design system, then two screens: **Home** and **Roadmap**. Dark is the default theme; light is equal.

## What Connexity is

Connexity is where a team checks on a fleet of conversational AI agents (mostly voice agents on platforms such as Retell, many of them built as conversational flows). The team's own AI assistant (Claude, ChatGPT or similar) does all the operational work through MCP: it watches, investigates and fixes. Connexity records every call, checks it, finds issues, scores the agents and keeps the roadmap.

The web app's only value next to the assistant is **a quick glance**: in a few seconds a person sees how the fleet is doing, what was found, and how fast things are improving. So every screen is a **dashboard**, not a report. It is not an observability tool: no trace explorers, no query builders, no drill-downs below a single call. The one filter is the period.

Starting state for the designs: the person connected Retell, everything has synced, and there are hundreds of calls across about 5 agents.

## Rules the screens must follow

- **Give before asking.** A screen opens with what Connexity found and how things are improving. Anything that needs the person is counted, never first.
- **Lead with the base, then keep it bare.** The first numbers are how many agents and how many calls, so every other number has context. A number tile is a label and a value, nothing else: no caption or source line under numbers or card titles.
- **Labels are one bare noun.** "Calls", "Issues", "Latency", not "Calls checked" or "Issues found". Cut any word the context already says.
- **Only checked agents appear.** An agent that has not been checked is not on the screen and not in any count.
- **Colour means a problem.** The interface is ink on neutral surfaces. Hue appears only for a state: critical, warning, passed, unchecked. Each state is always colour, icon and word together.
- **Orange is only the logo.** Never use it for buttons, links, charts or states.
- **No page-level "send to assistant" button.** The assistant is connected to everything through MCP. A small "Send to assistant" button exists only for immediate tasks (the next milestone's fixes).
- **It must work at real scale.** A fleet has thousands of issues. Never design something that only works with ten items.
- Sentence case everywhere. Plain, short words. No exclamation marks, no emoji.

## Design system

**Colour (dark / light):**

| Token | Dark | Light | Use |
|---|---|---|---|
| surface-0 | #121314 | #f5f4f2 | Page |
| surface-1 | #1a1b1d | #ffffff | Sidebar, tiles, cards, tables |
| surface-2 | #232427 | #ffffff | Menus, popovers, dialogs |
| border | #2a2c2f | #e3e1dd | Hairlines |
| border-control | #6b6f75 | #85837e | Control edges, neutral chart data |
| ink | #ececea | #17181a | Text |
| ink-secondary | #a3a5a9 | #5e6065 | Supporting text, labels |
| ink-muted | #8b8e93 | #6e7075 | Captions, timestamps |
| accent | #ececea | #17181a | The one main action (ink, not a hue) |
| on-accent | #121314 | #f5f4f2 | Text on accent |
| brand | #ee6a40 | #e8552a | Logo only |
| critical / critical-bg | #f59ab0 / #3a1420 | #a3173f / #fbe4ea | Critical (crimson, leans away from orange) |
| warning / warning-bg | #f2c46b / #33260f | #7a4d07 / #fbf0d9 | Warning |
| passed / passed-bg | #8fd3a9 / #14291d | #1c5c38 / #e2f2e8 | Passed |
| unchecked / unchecked-bg | #b5b7ba / #2a2b2e | #45474b / #ecebe8 | Unchecked, empty bar tracks |

All text pairs hold 4.5:1 in both themes.

**Type:** Figtree for everything, weights 400 and 500 only, tabular figures for numbers. JetBrains Mono only for IDs a person must copy. Sizes: 30 for tile numbers, 20 for page titles, 15 for body and table rows, 13 for labels, badges and table headers.

**Space and shape:** spacing 4, 8, 12, 16, 24, 32, 48. Radius 6 badges, 8 buttons and sidebar items, 12 tiles and cards. Cards have a hairline border and no shadow.

**Icons:** Lucide, outline. Severity icons: critical octagon-alert, warning triangle-alert, passed circle-check, unchecked circle-dashed.

**Components:** button (primary filled with accent, secondary outlined, ghost), severity badge, number tile, card, table, progress bar, sidebar item.

## Layout

- A sidebar 220px wide on surface-1 with a right hairline: the logo and "Connexity" at the top, then **Home, Agents, Roadmap, Issues, Settings**. The current page has a light wash and ink text; the others are ink-secondary.
- Each page opens with a page bar: the title, a muted caption with source and freshness ("Retell · synced 5 minutes ago"), and the period picker on the right where it applies.
- Then a row of number tiles, then cards in a grid, then tables. Content up to 1120px wide beside the sidebar.

## Screen 1: Home

1. **Page bar:** Home · Retell · synced 5 minutes ago · period picker "Last 30 days".
2. **Number tiles in one row:** Agents 5, Calls 838, Latency 1.1 s, Issues 23, Critical 3 (in critical colour), Warnings 16 (in warning colour), Clarifications 4.
   - Latency is the **average**, not p90.
   - "Clarifications" are the questions and inconsistencies the assistant could not settle on its own. They come in small batches (about 3 a week), answerable in the app or through the assistant.
3. **Two cards side by side:**
   - **Fleet score:** the score (59 / 100) large. Under it, one outlined box for the **next milestone only**: "Next milestone: 61", "1 of 3 points", a progress bar from the last milestone (58) to the next (61), and the fixes that make up this milestone as a checklist: each with a circle icon and its points; a finished fix has a green check and is struck through. A small quiet ghost button "Send to assistant" sits in the box header.
     - Score rules: **only fixes and improvements raise the score.** Answering questions, setting up process or a retest on its own never does. Each fix names a measurable target ("Get Car service booking's average latency under 1.5 s", not "answer faster"). A milestone is about 3 points.
   - **Calls per day:** a bar chart over the period. Bars are neutral; only calls with a **critical** issue are marked in critical colour (not warnings: nearly every call has some warning). Legend: "Calls", "With a critical issue". Under it, one line "3 clarifications this week" with an "Answer" button.
4. **Agents table, worst first:** Agent, Status (severity badge), Top issue, Calls, Latency, Issues, Score. A latency over its goal is in warning colour.

## Screen 2: Roadmap

The roadmap is the path from today's score to 99, and it covers **all** issues: thousands of them. It must show the direction, where we are on it, how fast we move, and when we get there. A person must be able to **reorganise it very quickly** when priorities shift.

1. **Page bar:** Roadmap · updated 2 hours ago. No send button.
2. **Number tiles:** Score 59, Goal 99, Issues left 3,208, Fixed a week 140, Goal by Jun 2027.
3. **"From 59 to 99":** one horizontal bar. The filled part is today's score; the remaining 40 points are split into segments, one per area, in priority order, sized by the points each area is worth and numbered by rank.
4. **Priorities: one ranked list of about 8 areas.** Issues are grouped so the list stays short at any scale, and each area is **named by the value it brings**, so it is recognised at a glance. Each row: drag handle and rank, a chevron and the area's name, a critical-count badge if it has open critical issues, a "fixed" progress bar with percentage, points it is worth, issues left, and a "done by" date. On hover: move to top, move up, move down.
   - Dragging a row reorders the list, the segment bar and every date. Dates come from the order and the fix rate: everything above an area is done first.
   - Clicking a row expands it into its 2 or 3 patterns, each with progress, points and issues left. Individual issues live on the Issues page, not here.

Example areas (placeholders): Callers are never cut off (+7, 412 left, 38 critical) · Every booking is confirmed (+6, 286 left, 21 critical) · Answers feel instant (+6, 530 left) · Facts are always right (+8, 690 left, 54 critical) · Callers are understood (+5, 610 left, 9 critical) · Callers are asked things once (+3, 340 left) · Callers reach a person when they ask (+4, 220 left, 12 critical) · Nothing private is said (+1, 120 left, 6 critical).

Example patterns inside "Callers are never cut off": Transfers that drop the call · Hang-ups during silence or hold · Calls ended before the caller finished.

## Placeholder data

Use invented agent names only: Insurance renewals, Restaurant reservations, Car service booking, Clinic after-hours, Dental reception. All numbers are placeholders.

## Rejected, do not bring back

- A text report with a headline sentence and paragraphs.
- Captions under numbers ("5 checked, 1 too new", "In 96 of 842 calls").
- A list of all agents in the sidebar.
- Opening a screen with "things that need you".
- Several milestones on home at once, or milestones without their fixes visibly inside them.
- A big filled "Send to assistant" button.
- A roadmap of a handful of cards in Now / Next / Later lanes, or a score line chart as the main roadmap view.
