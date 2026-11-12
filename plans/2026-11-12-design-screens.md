# Commit the Claude Design screens

- **Owner:** Dmytro
- **Slice:** none (reference material for every UI feature on the roadmap)
- **Design:** the Connexity project in Claude Design, exported by Dmytro on 2026-11-12
  ("Connexity design review"), committed as-is.
- **MCP:** None needed: documents only.

## Goal

Every session that builds a screen can see the approved design. Today the screens live
only in standalone Claude Design, which a Claude Code session cannot open, so a session
builds from the text prompts alone and the result drifts from what Dmytro designed.

## Changes

- **`designs/screens/`:** the export as Dmytro made it: one HTML page per screen (20
  pages) and `support.js`, the runtime they need. File names are kept, because the pages
  link to each other by name.
- **`designs/README.md`:** a Screens section that maps each page to what it shows and
  the milestone that builds it, says the exported page wins over the prompts for how a
  screen looks, and that the export is a snapshot replaced by a new export.

## Decisions

- Commit the export to the repo instead of linking standalone Claude Design (Dmytro:
  he exported it after the move into Claude was discussed).
- The names, agencies and emails in the pages are placeholders invented in Claude
  Design (Dmytro: "Approve, all fake").

## Done when

- `make check` passes.
- Each page opens in a browser from `designs/screens/`.
- No real client name, call data or private email is in the pages.

## Out of scope

- Moving the project into Claude; it can replace this export later.
- A "Design pages" column in the Notion roadmap; done outside the repo.

## Risks

- The export goes stale when a screen changes; the README says to re-export in a pull
  request.
- The pages load React from unpkg and fonts from Google, so they need a network
  connection to render.

## Outcome

### Deviations from the plan

None.

### Check results

| Step | Result |
|---|---|
| Plan present and complete | ok |
| Backend, MCP and frontend checks | ok (no code changed) |

The pages were scanned for private data: emails are all `@example.com`, and Dmytro
confirmed every person, agency and workspace name is invented.

### Not done

- Opening each page in a browser was left to Dmytro (the session does not open
  screens).
