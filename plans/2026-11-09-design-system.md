# Design system: a calm, dark-first product for reports and things to do

- **Owner:** Dmytro
- **Slice:** none (design foundation; the roadmap is paused until the design work is done)
- **Design:** [Connexity Design System](https://claude.ai/artifact/QcryjvPtMFxDiL2NcTNEv6),
  version 6 (`1794233506-0cb8`). Dmytro approved the foundations at version 4
  ("everything else approved") and the components at version 5 ("Approve components").
  Version 6 changes only the wording of the Input note, to match the docs in this change.
- **MCP:** None needed: design and documents only. Nothing a user can do or see in the
  running product changes.

## Goal

There is a design system for Connexity 2.0 in Claude, and every later screen design is
built on it. It describes a product that is easy to read, not an observability tool:
people open it to see a short report and to approve or answer the few things that need
them. The assistant does all the other work.

The repo docs say the same. Today they still say the UI may do anything the API does,
and they still park a calls screen and a drill-down screen. After this merges they
describe the web app as reports and things to do, plus a view of a single call.

## Changes

**The Design System artifact (in Claude, not in the repo).** Split into files as the
lifecycle guide requires:

- **Foundations:** colour tokens for dark (designed first) and light. The logo orange is
  used only for the logo. Ink is the accent, and colour inside the product means a problem:
  four severity states (critical, warning, passed, unchecked), each with an icon and a
  label as well as a colour. Type: Figtree for everything, tabular figures, a monospace
  face only for IDs a person needs to copy. A type scale that starts larger than a
  dashboard's (13 labels, 15 report text, 16 things to do, 20 headings, 30 the one
  headline number). Spacing, radius and elevation.
- **Assets:** the logo (the three loops) and its tone-on-tone version. The loops also
  become the favicon, replacing the teal "F".
- **Primitives:** only what the app uses: button, input, select, checkbox, switch,
  dialog, sheet, menu, tabs, table, skeleton, toast. Restyled shadcn/Radix, so the
  design maps onto the components the code already has.
- **Product pieces:**
  - a to-do item, either an approval (a fix the assistant prepared) or a question with
    answer buttons
  - a report line (an agent's status in one sentence)
  - a severity badge
  - the parts of a single-call view: the recording player and the transcript

**Documents in the repo:**

- `CLAUDE.md`, `frontend/CLAUDE.md` and lifecycle section 6 no longer say the UI may do
  anything the API does. They say the web app shows reports and things to do, plus a
  view of a single call. Everything else is the assistant's, through MCP. The rule that
  every feature ships with MCP tools stays.
- Lifecycle section 3: the open question "whether UI work waits for the design system"
  is answered.
- `REBUILD.md`:
  - the decisions are added to the decision log
  - the "Kept after checking the code" row that cites the 2026-10-09 rule is updated
  - parked slice 1.7 (calls screen) is narrowed to the single-call view
  - parked slice 2.5 (findings, issues and incidents on screen, drilled down to the
    moment) is deleted

**No frontend code changes.** The code stays on stock shadcn tokens until a later slice
moves it onto the design system. The design may be ahead of the code; it may never be
behind it.

## Decisions

Made by Dmytro on 2026-11-09:

- Start the design from scratch, and start with the design system ("I want to start
  working on design from scratch… Probably we need to start with design system").
- The logo is the one thing that exists and will not change. The teal "F" favicon is a
  leftover ("1. yes"). There are no other logo rules.
- Dark mode is equal to light, if not first ("i like dark mode as equal if not first").
- Connexity is not an observability platform and must be much easier to read than
  Linear, Sentry, Grafana, Datadog or Vercel. The frontend shows only the most important
  things: reports and things to do. It is extremely friendly, intuitive and simple.
  Drilling down from an incident to traces "doesn't make any sense now", because all of
  the work is done through the assistant.
- The rule "the UI may do anything the API does" (2026-10-09) is retired ("Retire it").
- A person can open a single call: its recording and transcript, linked from a report or
  a to-do ("User can do that").
- Typeface: Figtree ("B").

Proposed by Claude, not separately confirmed:

- Keep shadcn/Radix and Tailwind v4 underneath and redesign only the visual layer.
- The logo orange is used only in the logo, ink is the accent, and colour inside the
  product only marks a problem. (Shown as a drawing; Dmytro moved on without objecting,
  which is not approval.)
- Dark is the default theme on first open.
- The type scale above, and keeping monospace only for copyable IDs.
- Delete parked slice 2.5 and narrow 1.7, rather than keeping them as parked ideas.
- The code moves onto the design system in a later slice, not in this one.

Open:

- The logo's vector source and exact hex. Dmytro will find them; until then the design
  system uses the PNG and an approximate #E8552A.

## Done when

- The Design System artifact exists in Claude with the foundations, assets, primitives
  and product pieces listed above, each in its own file, in dark and light.
- Dmytro has reviewed it and approved a version, and that version is named in the
  Design line at the top of this plan.
- No document in the repo outside `plans/` and the decision-log history says the UI may
  do anything the API does.
- `REBUILD.md` holds the decisions above, in Dmytro's words.
- `make check` passes.

## Out of scope

- Any screen design (home, report, single call, settings). Each one is designed on the
  system next, one at a time.
- Any frontend code, including the favicon swap.
- Rewriting the roadmap.
- Dmytro's private vision. Its "Conflicts" section still lists the UI question as
  unresolved; he updates that file himself.

## Risks

- **The logo colour is approximate** until the source file arrives. The palette may need
  a small shift then.
- **Too little to build on.** A system this small could miss a piece a screen needs. That
  is the intent: a piece is added when a screen design needs it, not before.
- **Code and design drift apart for a while**, with the code still on stock tokens. That
  is allowed, because the design is ahead, but it should not last long.
- **Deleting 2.5 loses the incident drill-down idea.** It is recoverable from git history
  and from this plan.

## Outcome

### Deviations from the plan

- **The cover has no pattern.** The first cover had discs that grew in size, echoing the logo. Dmytro
  asked what they were for, and they were removed ("yes remove it"), because decoration
  that looks like it means something works against the product. The cover file says so.
- **The root `CLAUDE.md` never stated the retired rule.** Instead it gains one sentence:
  the web app is reports, things to do and a single call, built from the design system.
- **The lifecycle guide changed in two more places than planned.** Its "Path" paragraph
  now says technical depth lives in the record and is reached through MCP. Its
  design-system bullet now names the artifact and the order (system first, then
  screens).
- **Which forms stay is Proposed, not Decided.** The docs say forms stay only where a
  person must act themselves, such as signing in. Connections, agents and settings are
  the assistant's.
- **The create-agent and Integrations forms are not removed.** `REBUILD.md` now marks
  them for removal when the frontend moves onto the design system, and says to ask
  first.
- **Icons are copied, not loaded.** The design system bundle carries the nine Lucide icons
  the components use (severity, play, pause, chevron, check, close) as inline paths,
  because previews cannot import `lucide-react`. The code will use `lucide-react` itself.
- **The Proposed choices were approved with the foundations and components:** ink as the
  accent, orange only in the logo, dark as the first theme, the type scale, and
  shadcn/Radix kept underneath.

### Check results

`make check` on this branch: every step passed in one run.

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 1s |
| Start local database | ok | 1s |
| Backend lint and format | ok | 1s |
| Backend types (pyright) | ok | 55s |
| Backend tests and coverage | ok | 275s |
| MCP server tests | ok | 7s |
| Frontend lint | ok | 6s |
| Frontend types | ok | 6s |
| Generated client is fresh | ok | 24s |

All 17 component previews were rendered once with React's server renderer, without
errors, and the bundle parses. The system was not looked at in a browser by the session.
Dmytro reviewed it in Claude.

The colour pairs were checked numerically (WCAG 2): every text pair reads at 4.5:1 or better on the surfaces its
note names, in both themes, and `border-control` and `focus-ring` read at 3:1 or better
on every surface.

`/code-review` was not run: no code in the repo changed, only documents and this plan.
The design system's bundle lives in the artifact, not in the repo.

For Dmytro to check: nothing on screen changes in the app. Open the design system link
above and switch between dark and light.

### Not done

- The logo's vector source and exact hex. The system uses the PNG and an estimated
  `#E8552A` (`#EE6A40` in dark) until Dmytro finds them.
- No frontend code moved onto the design system, by plan.
