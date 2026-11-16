# The Work page: design and decisions

- **Owner:** Dmytro
- **Slice:** none yet. It is design and context for the Work page, which follows the
  "Next task for the assistant" feature in the Demo milestone. No roadmap row builds the
  page yet.
- **Design:** the Connexity project in Claude Design, exported by Dmytro on 2026-11-16
  ("Connexity design review (8)"), committed as-is.
- **MCP:** None needed: documents and design only. The Work page's MCP side is
  `get_next_task`, planned in its own pull request.

## Goal

Every session can read what the Work page is and why, before building it or the features
around it. Today the decisions behind it exist only in a design conversation. The repo
still says the sidebar has Home, Action items and Roadmap, and a session planning 10.123
or Action items work would build what this design replaces.

## Changes

- **`designs/screens/`:** the 2026-11-16 export:
  - the new **Work** page, with its frames: onboarding with no assistant, onboarding with
    the assistant working, working, answering questions, and details;
  - the sidebar with Work first and Home renamed Dashboard, with no Action items or
    Roadmap entries;
  - the updated Roadmap and Action items pages, which are now superseded.
- **`designs/16-work.md`:** the prompt that gives the Work page, with every adjustment
  folded in.
- **`docs-internal/work.md`:** the decisions about Work, each with Dmytro's words, plus
  what is only Proposed and the open questions. It wins over the prompt.
- **`designs/README.md`:** lists prompts 01 to 16, adds the Work page, marks Roadmap and
  Action items as superseded, and moves the export date to 2026-11-16.
- **The sidebar rule** in `docs-internal/development-lifecycle.md` and
  `frontend/CLAUDE.md`: Work, Dashboard, Incidents, Agents, Calls, Issues, Settings, and
  the person lands on Work.
- **`REBUILD.md` decision log:** two lines, one for Work and one for no suggested answers
  in Connexity.
- **`docs-internal/README.md`:** links the new doc.

## Decisions

- Everything in `docs-internal/work.md` under "Decided" is Dmytro's, quoted there
  (2026-11-15 and 2026-11-16).
- Commit the export as-is, including the superseded Roadmap and Action items pages, so
  the export stays one snapshot (Proposed).
- `designs/15-assistant-tasks.md` is not added here. It comes with the next task pull
  request, and prompt 16 supersedes it (Proposed).
- The decisions live in `docs-internal/` rather than `designs/`, so they win over prompts
  under the existing "which source wins" rule (Proposed).

## Done when

- `make check` passes.
- `Connexity Work.dc.html` opens from `designs/screens/` and shows the frames listed
  above.
- No real client name, call data or private email is in the pages or docs.
- No committed file links to Notion or quotes Dmytro's private vision.

## Out of scope

- Building the Work page, removing the Action items page, or renaming Home in the app.
- What happens to 10.123's stored suggestions (#207) and its confirm panel (#208). This
  change records the conflict as open and does not decide it.
- The zoomed-out roadmap and goals, which are parked until after the demo.
- Notion roadmap rows for Work.

## Risks

- The repo now describes a sidebar the app doesn't have yet. Rule 14 still holds: a
  build shows only what works, and the docs describe the target.
- "Give before asking" in `frontend/CLAUDE.md` says what needs the person is never
  first, while Work puts a waiting task at the top of In progress. A reviewer should ask
  Dmytro which rule wins on Work.
- #208 is open and builds the confirm panel this design rules out. It should not merge
  before Dmytro decides.

## Outcome

### Deviations from the plan

- After a separate review, four changes:
  - `designs/README.md` also marks the Onboarding page as superseded by onboarding tasks
    on Work.
  - `docs-internal/work.md` gains open question 11 ("give before asking" against Work's
    top row), with a note under that rule in `frontend/CLAUDE.md`.
  - Decision 18 now quotes Dmytro.
  - `designs/16-work.md` lists the export's six frames and the three places where the
    export differs from the prompt (a dot instead of a pause icon, "blocks:" and "Up
    next", a leftover link to Action items), and says to build to the prompt.

### Check results

| Step | Result |
|---|---|
| Plan present and complete | ok |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

`make check` ran in a fresh worktree with Python 3.12. No code changed.

The pages and docs were scanned for private data. Emails are `@example.com`, plus the
invented `brightdental.com` and `agency.com` already on main. People and agents are the
existing placeholders. A separate review found no public-repo concerns and no broken
links.

### For Dmytro to check on screen

- Open `designs/screens/Connexity Work.dc.html` and check its frames: onboarding with no
  assistant, onboarding with the assistant working, working, answering, answered, and
  details.

### Not done

- The tension between "give before asking" and Work's top row is recorded as open, not
  resolved.
- Notion roadmap rows for building Work are not part of this change.
