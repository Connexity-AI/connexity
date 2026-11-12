# Prompt for Claude Design: the roadmap as milestones

Paste everything below the line into the existing Connexity project in Claude Design. It replaces the Roadmap's ranked list of areas.

---

Redesign the Roadmap around **milestones**, in dark and light, using the existing design system, sidebar and page bar. The roadmap is the path from today's score to 99, and it must show at a glance: the direction, where we are on it, how fast we move, and when we get to each step.

## How milestones work

- A milestone is a step of about 3 points of score. From 59 to 99 that is about 13 milestones.
- Only fixes raise the score. Each milestone holds the fixes that make up its points. At real scale a milestone holds dozens or hundreds of issues, so its content is shown grouped, never as a flat list.
- Fixes are labelled with the app's fixed categories (Booking, Transfers and escalation, Responsiveness, Pricing and quotes, and so on), so people recognise what a milestone is about.
- Dates come from the pace: points gained per week.

## The page

1. **Page bar:** "Roadmap", muted "Updated 2 hours ago". No buttons.
2. **Number tiles:** Score 59, Goal 99, Pace +3 a week, Next milestone 61, Goal by Jun 2027.
3. **The path:** one horizontal track from today's score to 99, with a dot for each milestone. Reached milestones are filled, the current one is larger with "Now", later ones are hollow, each with its expected date underneath. The person sees in one line how far they are and how far is left.
4. **Milestones list,** in order:
   - **Reached** milestones collapse into one quiet line at the top: "6 milestones reached since 12 Oct", expandable.
   - **The current milestone** is open: "Milestone 61 · by 16 Nov", progress "1 of 3 points", a progress bar, then its content grouped by category. Each category row shows the category name, how many issues it fixes, how many are done, and the points it is worth. Expanding a category shows the patterns inside it (for example under Transfers and escalation: "Transfers that drop the call · 42 issues"), not individual issues.
   - **Upcoming milestones** are collapsed rows: milestone target and expected date, its categories as small labels with counts ("Booking 38 · Responsiveness 24 · Pricing and quotes 12"), and its points. Expanding one shows the same grouped content as the current milestone.
5. **Shifting priorities, fast:**
   - Drag a category group (or a single pattern) from one milestone to another to do it sooner or later. Hovering a group also shows a small "Move to" menu listing the milestones by target and date.
   - Drag whole milestones to reorder them.
   - Every move recalculates the milestones' targets and dates at once, so the person immediately sees what doing something sooner costs everything after it.

Placeholder milestones: 61 by 16 Nov (current: Transfers and escalation 42, Booking 18, Information collection 9), 64 by 23 Nov (Booking 38, Responsiveness 24, Pricing and quotes 12), 67 by 30 Nov (Pricing and quotes 51, Speech recognition 20), 70 by 7 Dec (Responsiveness 64, Ending the call 15), and so on to 99. All numbers are placeholders.
