# Frontend foundation on the design system

- **Owner:** Dmytro
- **Slice:** Milestone 1, feature 1 of the roadmap: "Frontend foundation on the design
  system".
- **Design:** the Claude Design export of 2026-11-12, committed under `designs/screens/`
  (PR #178), as Dmytro named it for this feature:
  - `Connexity Design System.dc.html`: colour tokens in dark and light, type, space,
    radius, and the components (button, severity badge, sidebar item, number tile,
    progress bar, card with table, Lucide icons).
  - `Connexity Sidebar.dc.html`: the sidebar, the profile area and its menu.
  - `Connexity Onboarding.dc.html`: the page frame beside the sidebar (padding, page
    title, content width). Its Readiness content is feature 4, not this one.
- **MCP:** None needed. This change deletes 1.x screens and builds an empty shell. No
  backend route or MCP tool changes, and nothing the assistant can do through MCP
  changes. The only new things a person can do are pick a theme and sign out, which
  belong to the person's browser, not the workspace.

## Goal

The web app stops showing 1.x and starts on the Connexity Design System. After this
merges:

- No 1.x screen is left: no agent tabs, eval screens, metrics, integrations or LLM-key
  onboarding.
- A signed-in person sees the 2.0 shell from the design: the sidebar with the logo, and
  the profile menu at the bottom with Theme and Sign out.
- The page bar and the number tile exist as components, ready for the first pages
  (Readiness, Calls, Agents) to use.
- Nothing on screen that does not work: the sidebar lists no page until that page's
  feature is built (`CLAUDE.md` rule 14).

## Changes

### Step 0: delete the 1.x screens (approved by Dmytro)

Frontend only. Every backend route stays, because the assistant, the CLI and the frozen
eval stack still use them.

| # | Screen | Route | What goes with it |
|---|---|---|---|
| 1 | Agent: calls ("Observe") | `/agents/[id]/observe` | Calls table, call drawer, "make test case from call" panel, date-range picker |
| 2 | Agent: environments | `/agents/[id]/environments` | Environments tab |
| 3 | Agent: evals | `/agents/[id]/evals/*` | Test cases list and drawer, eval configs list and detail form, eval runs list and detail, the "Run" button, LLM model picker |
| 4 | Agent header | `/agents/[id]` layout | Breadcrumb, mode tabs, agent header |
| 5 | Agents list and create-agent form | `/agents` | New-agent modal and its schema |
| 6 | Metrics | `/metrics` | Custom metrics page |
| 7 | Integrations | `/integrations` | Add and delete integration dialogs, cards |
| 8 | LLM-key onboarding | `/onboarding` | The redirect in the app layout that forces it, the LLM keys dialog in the user menu |
| 9 | Old shell | every signed-in page | Sidebar, header, user menu, theme toggle, page title, the teal "F" favicon, the Inter font, the redirects from `/` to `/agents` |
| 10 | Code only these screens use | — | Server actions (agents, calls, environments, eval configs, runs, test cases, custom metrics, integrations, and any other nothing imports afterwards), their query keys, URL builders and parsers, form schemas, the shared data table, shadcn primitives in `packages/ui` that nothing imports afterwards |

Each page that comes back is rebuilt from the new design by its own feature: the Calls
page (11), the single call (13), the Agents page (15). The backend eval stack stays
frozen, not deleted; the backend LLM-key routes stay for the judges.

Kept: sign in (`/login`), sign up (`/register`), the auth, client-proxy and health API
routes, the error and not-found pages, robots and sitemap, the providers, and the
generated client.

### The shell, as in the design

- **Tokens.** The shadcn colour variables are replaced by the design system's tokens,
  with the values in `Connexity Design System.dc.html`: surface-0 to 2, border,
  border-control, ink, ink-secondary, ink-muted, accent, on-accent, **wash** (current
  sidebar item and row hover, new since the prompts), brand, and the four severity
  pairs, in dark and light. Orange appears only in the logo.
- **Type.** Figtree for everything (400 and 500, tabular figures); JetBrains Mono only
  for IDs a person copies. Sizes 30 tile number, 20 page title, 15 body, 13 labels.
  Loaded with `next/font`, not from Google at runtime.
- **Space and radius.** 4, 8, 12, 16, 24, 32, 48; radius 6 badge, 8 button and sidebar
  item, 12 tile and card. Cards have a hairline and no shadow; the profile menu has the
  design's soft shadow.
- **Theme.** Dark, Light and System, picked in the profile menu and remembered in the
  browser. First open: question 2 below.
- **Sidebar** (`Connexity Sidebar.dc.html`). 220px on surface-1 with a right hairline,
  padding 16 by 12. The logo and "Connexity" (15, 500) at the top. Then the page list:
  items 36px high, 16px Lucide icon, 15px label, the current page on wash in ink, the
  others in ink-secondary. The order is Home, Incidents, Action items, Agents, Calls,
  Roadmap, Issues, Settings, but **each entry appears only when its feature ships; in
  this change the list is empty**. The design's counts, the incident glimmer, the
  Readiness ring and "Credits low" come with their features.
- **Profile area.** Pinned to the bottom above a hairline: initials avatar, the person's
  name (email when there is no name), and the chevrons-up-down icon. The workspace name
  under the name comes with workspaces (feature 3).
- **Profile menu.** Opens above the profile area on surface-2, closes on an outside
  click. In this change: **Theme** (Dark, Light, System, as a segmented control) and,
  after a divider, **Sign out**. The Workspaces part (list, search, New workspace,
  Agency settings) and Account appear when their features ship.
- **Page frame** (`Connexity Onboarding.dc.html`). Main area on surface-0, padding 24
  top, 32 sides, 48 bottom.
- **Page bar.** A component: the title (20, 500) on the left, a slot on the right, and a
  muted caption, at least 40px high. Not used by any page in this change.
- **Number tile.** A component from the design system: surface-1, hairline, radius 12,
  padding 16; a 13px label in ink-secondary and a 30px value. A severity tile puts the
  icon and the label in the severity colour, and the value too. Not used by any page in
  this change.
- **Where a signed-in person lands:** question 1 below.
- **Sign in and sign up** keep their layout and pick up the new tokens and font, so they
  do not look like a different product. They are redesigned with "Sign up and log in"
  (feature 3).

## Decisions

Decided by Dmytro:

- Step 0: "You can remove anything you need, we will need to recreate it with new
  Claude design" (2026-11-12). This approves the ten rows above, including the
  create-agent form and the Integrations page that `REBUILD.md` marked "ask first".
- The design for the shell is `Connexity Sidebar.dc.html`, `Connexity
  Onboarding.dc.html` and `Connexity Design System.dc.html` from the 2026-11-12 export
  (2026-11-12).
- Earlier, applied here: Figtree; dark equal to light, if not first; the logo is fixed
  and the teal "F" is a leftover (2026-11-09). The sidebar order, and the profile menu
  holding the workspace picker, Account, Theme and Sign out (2026-11-12). Nothing in the
  UI that does not work end to end (2026-11-12).

Proposed by Claude:

- The sidebar ships empty; each later feature adds its own entry. The Onboarding export
  shows every entry before the first scan, but rule 14 wins over the design here.
- The profile menu has only Theme and Sign out until Account and workspaces exist.
- Page bar and tile live in `packages/ui` next to the other primitives.
- Sign in and sign up take the new tokens without a layout change until feature 3.
- shadcn/Radix and Tailwind stay underneath.

## Open questions

1. **The landing page.** No Milestone 1 page exists until Readiness (feature 4).
   Proposed: a signed-in person sees the shell with an empty content area.
2. **The theme on first open.** The Sidebar export falls back to **System** when nothing
   is stored; the design-system plan said **Dark** on first open. Proposed: follow the
   export (System), since the design wins over older text.
3. **The logo.** The Sidebar export draws two orange circles, not the three-loop mark.
   Proposed: use the real three-loop mark (`connexity-logo.avif`, also as the new
   favicon) at the export's size, and correct the design to match.

## Done when

- `make check` passes, and `next build` passes.
- No file under `frontend/` imports a deleted route, action or component, and
  `/agents`, `/metrics`, `/integrations` and `/onboarding` return the not-found page.
- Every colour in the app comes from a design-system token; a search for the old
  shadcn colour names and for raw hex values outside the token file finds nothing.
- The backend test suite and the MCP server tests pass unchanged (nothing there moved).
- Dmytro, on screen, next to the three design files:
  1. Signing in lands on the shell with the logo and favicon.
  2. The sidebar matches `Connexity Sidebar.dc.html` with no page entries.
  3. The profile menu switches between Dark, Light and System, the colours match the
     design system in both themes, and the choice survives a reload.
  4. Sign out returns to the sign-in page, and the old URLs above show not found.
  5. Sign in and sign up still work, in both themes.

## Out of scope

- Any page: Readiness, Calls, Agents, the single call, Home. Each is its own feature.
- Workspaces and the workspace picker (feature 3), the Account page, Agency settings.
- The Readiness ring and stripe, incident counts and glimmer, credits.
- Backend and MCP changes, including deleting `Environment` or the eval routes.
- A narrow-screen layout; the designs have none (the Onboarding frame sets a 944px
  minimum).

## Risks

- **For a while the app shows almost nothing.** Between this merge and the Readiness
  page, a signed-in person sees an empty shell. That is rule 14 working.
- **The frozen eval stack loses its screens.** Its backend stays and is still reached
  through the API and the CLI.
- **Deleting shared code can break sign in.** The data table, actions and providers are
  tangled; the build and a manual sign-in check are what catch it.
- **Primitives deleted now may be wanted later.** They come back from shadcn in one
  command, restyled by the tokens.

## Outcome

Dmytro answered the open questions with "Accept, build": the landing page is the empty
shell, the theme on first open follows the system, and the sidebar uses the real
three-loop logo.

### Deviations from the plan

- **The shadcn colour names stay, as aliases.** "Done when" said a search for them would
  find nothing. Instead, `theme-default.css` holds every colour value once, as design
  tokens, and maps the shadcn names (`background`, `primary`, `border` and so on) onto
  them, so the remaining primitives work unchanged. No raw palette class or hex value is
  left outside that file.
- **More primitives went than expected.** Only seven are left in `packages/ui`: button,
  dropdown menu, form, input, label, toast and toaster. The rest, including ones the
  design system lists (table, tabs, select, checkbox, switch, dialog, sheet, skeleton),
  had no importer after step 0. Each feature adds back what it needs.
- **Dependencies only the deleted code used were removed:** Monaco, TanStack Table,
  date-fns, the day picker, react-icons, set-cookie-parser in the app, and about thirty
  Radix and helper packages in `packages/ui`.
- **The button was rewritten** to the design system's three variants (primary,
  secondary, ghost). The old sizes, icon props and the success, outline, link and
  destructive variants are gone; nothing used them after step 0.
- **The error pages** (not found, global error, the error boundary) moved off raw red,
  grey and teal classes onto the tokens, without a layout change. Headings everywhere
  left use weight 500 and the 20px title size, because only 400 and 500 are loaded.
- **The browser title** is now "Connexity" instead of the 1.x positioning.
- **`docs/traces/n8n.md`** no longer points to the deleted Integrations page.
- **The logo** is the existing `connexity-logo.avif` (the three loops, tone on tone, on
  orange) at 22px. The favicon is the same image at 64px. A duplicate favicon in
  `packages/ui` that nothing used was deleted.
- **`/`** is a page of its own in the signed-in group and renders nothing; the old
  redirects to `/agents` are gone. After sign-in the app lands there.

### Check results

`make check` on this branch, before this Outcome was written (the plan step failed only
because this section was empty):

| Step | Result | Time |
|---|---|---|
| Plan present and complete | failed (Outcome empty) | 0s |
| Start local database | ok | 1s |
| Backend lint and format | ok | 1s |
| Backend types (pyright) | ok | 9s |
| Backend tests and coverage | ok | 87s |
| MCP server tests | ok | 3s |
| Frontend lint | ok | 6s |
| Frontend types | ok | 5s |
| Generated client is fresh | ok | 7s |

`next build` passes. The built CSS contains every new token class the shell uses
(surfaces, hairline, ink levels, wash, accent, severity, type sizes, menu shadow). The
build lists only `/`, `/login`, `/register`, the not-found page, the API routes, robots
and sitemap.

`/code-review` (high) raised eight findings. Fixed: the font token broke where the
Figtree variable is unset (the global error page), the n8n doc, `REBUILD.md`, the 1.x
browser title, the duplicate favicon. Not fixed, listed below: the global error page's
theme, keyboard access to the theme picker, and the logo's design.

**For Dmytro to check on screen**, next to the three design files:

1. Sign in: the app lands on `/` with the sidebar and an empty content area. The tab
   shows the orange favicon and the title "Connexity".
2. The sidebar matches `Connexity Sidebar.dc.html`: 220px, the logo and "Connexity" at
   the top, no page entries, your name (or email) at the bottom above a hairline.
3. The profile menu opens upward. It has Theme (Dark, Light, System) and Sign out. Dark
   and Light match the design system's colours. The choice survives a reload. System
   follows the operating system.
4. Sign out returns to the sign-in page. `/agents`, `/metrics`, `/integrations` and
   `/onboarding` show the not-found page.
5. Sign in and sign up still work, in both themes, in Figtree.

### Not done

- **The Sidebar design shows a different mark.** Dmytro corrects the Sidebar export to
  the three-loop logo, as agreed, so the design is not behind the code.
- **The global error page is always light.** It renders its own page outside the theme
  provider, so it cannot know the chosen theme.
- **The theme picker inside the menu is reached with Tab, not the arrow keys.**
- **No screen was opened by the session**, by the frontend rule; the checks above are
  Dmytro's.
- **Nothing is committed or pushed.**
