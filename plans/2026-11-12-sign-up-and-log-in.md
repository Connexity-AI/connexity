# Sign up and log in, with workspaces from the start

- **Owner:** Dmytro
- **Slice:** Milestone 1, feature 3 of the roadmap: "Sign up and log in".
- **Design:** the Claude Design export "Connexity design review" of 2026-11-12 (17:11),
  committed under `designs/screens/`, from prompt `designs/13-sign-in-and-workspaces.md`:
  - `Connexity Sign in.dc.html`: sign in, create an account, and connect an assistant,
    with their error states.
  - `Connexity Sidebar.dc.html`: the profile menu's Workspaces part (scrolls past six,
    search past eight, no "Agency settings") and the New workspace dialog.
  - Also updated in the export: `Connexity Home.dc.html` (passes the dialog state to the
    sidebar) and the `Connexity.dc.html` index.
- **MCP:** `list_workspaces` returns every workspace the person belongs to. Adds
  `create_workspace(name)`, so the assistant can do what the "New workspace" item does.

## Goal

A person can sign up and sign in with email and password, or with Google, and lands in
the app. From the start they can have several workspaces (one per client), create one,
and switch between them from the profile menu. There are no members and no agency
settings yet. Everything else built so far keeps working, scoped to the workspace that
is open.

## What exists today

- **Email and password** sign-up and sign-in (`/users/signup`, `/login/access-token`),
  with an HttpOnly cookie JWT that carries the company (`cid`). The OAuth flow the MCP
  server uses has its own sign-up form.
- **No Google.** `AuthProvider` has `email` and an unused `github`.
- **One company per person** (`user.company_id`), used by about 215 lines of route code
  to scope data. Since the MCP foundation, a company is a workspace with a name, and
  MCP access is decided in `crud/workspace.py`.
- **Leftovers:** `/users/me/onboarding-status` and the `has_llm_key` /
  `onboarding_complete` fields served the LLM-key onboarding screen deleted in M1.1.
  Nothing uses them.
- **A bug:** the OAuth sign-up form answers 500 for an email that fails validation,
  instead of showing the form with an error (found in the MCP foundation play-through).

## Changes

### Step 0: the design (before any frontend code)

Written: the Claude Design prompt `designs/13-sign-in-and-workspaces.md`, for:

- the sign-in page and the sign-up page, with "Continue with Google";
- the "New workspace" step from the profile menu: name only;
- the error states: a wrong password, an email already used, and Google refused.
- the page a person sees when their assistant asks to connect (the OAuth sign-in and
  approve page the backend renders today), signed out and signed in.

You design it in Claude Design and approve a version. This plan's Design line then
names that export.

### Workspaces (backend)

- **Membership.** A `workspace_member` table joins a person to the workspaces they
  belong to. Every existing person becomes a member of their company. Access in
  `crud/workspace.py` reads this table, so MCP scoping follows without other changes.
- **The open workspace.** `user.company_id` becomes "the workspace this person has open"
  and keeps scoping every web route, unchanged. Switching checks membership, updates it
  and reissues the session cookie with the new `cid`. MCP calls are unaffected: they
  name their workspace on each call.
- **Creating a workspace** (web and MCP): a name, 1 to 255 characters. The creator
  becomes its member and, on the web, it opens.
- **Signing up** creates the first workspace, named from the email domain as today.

### Google sign-in (backend and frontend)

- Sign in with Google by OpenID Connect: the backend sends the person to Google and
  receives the callback. A first Google sign-in with an unknown email creates the
  account and its first workspace. A known email signs in to that account, whether it
  was made with a password or with Google.
- New settings: `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, added to `.env.example`.
  With them unset, the Google button does not appear.
- The OAuth flow the MCP server uses gets "Continue with Google" too, so a person can
  connect an assistant without a password.
- `AuthProvider` becomes `email` and `google`; `github` is removed.
- The assistant-connection page the backend renders (sign in, sign up, approve) is rebuilt
  from the design, with the design system's tokens.

### Screens (frontend, from the approved design)

- Sign-in and sign-up rebuilt from the design, with "Continue with Google".
- The profile menu gains its Workspaces part as in `Connexity Sidebar.dc.html`:
  - the person's workspaces, with the open one ticked;
  - a search field when there are more than eight;
  - **New workspace**.
  "Agency settings" stays out until it exists.
- The profile area shows the open workspace's name under the person's name.
- After sign-up or sign-in the app opens on `/`. That is the empty shell until Readiness
  (feature 4) takes it over; the roadmap's "opens on Readiness" lands with feature 4.

### Clean-up

- Delete `/users/me/onboarding-status` and the `has_llm_key` / `onboarding_complete`
  fields.
- Fix the 500 on an invalid email in the OAuth sign-up form.

## Decisions

Decided by Dmytro earlier, applied here:

- A workspace per client; MCP reaches the person's workspaces; the workspace picker
  lives in the profile menu with the workspace name under the person's name; no
  white-labelling (2026-11-12).
- Sign-in methods are email and password, and Google (`12-adjustments.md` item 23,
  roadmap entry).
- No members or agency settings yet (roadmap entry).

Proposed by Claude:

- A membership table now, rather than a workspace column on the person.
- `user.company_id` as the open workspace, so web routes need no change.
- A known email signs in with Google into the existing account.
- The Google button is hidden when Google is not configured.
- `create_workspace` as an MCP tool.
- Remove `github` from `AuthProvider`, and the onboarding-status leftovers.

## Answered questions

Dmytro accepted the plan and its recommendations ("Accept", 2026-11-12):

1. **The design:** I write the Claude Design prompt as step 0
   (`designs/13-sign-in-and-workspaces.md`). Dmytro designs and approves it before any
   frontend code.
2. **Google credentials:** not answered. Google is built against mocks, and the
   Outcome lists the setup steps for a Google Cloud OAuth client. It is tested for real
   once Dmytro provides `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
3. **Two tabs:** the open workspace lives on the person, and switching in one tab
   switches the others. Accepted for now.
4. **Password reset and email verification:** out of scope for this feature.

## Done when

- `make check` passes; backend tests cover:
  - membership and switching (a non-member is refused);
  - creating a workspace (web and MCP);
  - Google sign-in for a new email and for a known email, with Google mocked;
  - the OAuth sign-up form showing an invalid email as an error.
- Played through the API on a running server: sign up, create a second workspace,
  switch, see its (empty) agents, switch back, and see the first workspace's agents.
  Through MCP, `list_workspaces` returns both and `create_workspace` adds a third.
- Dmytro, on screen:
  1. sign up with email and land in the shell, with the workspace name under your name;
  2. sign out and back in, with email and with Google;
  3. create a workspace from the profile menu and switch between workspaces;
  4. in both themes, everything matches the approved design.

## Out of scope

- Members, invitations, roles, "can approve", agency accounts and Agency settings
  (Milestone 9).
- The Account page (profile, password change, sessions, assistant access).
- Renaming or deleting a workspace.
- Password reset, email verification and two-step verification (question 4).
- The Readiness screen (feature 4).

## Risks

- **Scoping by the open workspace is global per person** (question 3). A route that
  forgets it is unaffected, but two tabs can surprise.
- **Account linking by email** trusts Google's verified email. An unverified Google
  email must be refused; a reviewer should check that this is tested.
- **The migration** adds a membership for every existing person. A person whose company
  was reassigned by hand keeps only their current company.

## Outcome

### Deviations from the plan

- **Google on the assistant-connection page is not built.** That page runs on the MCP
  server's address, but Google's callback lands on the backend's address. A cookie set on
  one does not reach the other, so Google there needs the callback to come through the
  MCP address. The page shows the design's "deployment without Google" state. Google
  sign-in works for the web app.
- **The connection page gained the design's approval step.** Before, a signed-in person
  got a code with no question asked. Now they see "Connect … to Connexity" with Allow
  and Cancel, after signing in, after creating an account, or on arriving signed in.
  - Allow hands the code over.
  - Cancel answers the assistant with OAuth's `access_denied`; the assistant shows its own
    message, not the design's "was not connected" line.
  - "Not you?" signs out on that page.
  - The pages carry the design system's colours (dark, or light when the browser prefers
    it), the three-loop logo, and cannot be framed by another site.
- **What the design changed:**
  - Passwords need 8 characters (6 before). Existing shorter passwords still sign in;
    the current password in "change password" needs only 1 character.
  - First workspaces are named like "Bright Dental", or "My workspace" without a domain.
    Existing names stay.
  - The sign-up form has no "confirm password" field.
- **The session cookie check changed.** It used to require the cookie's workspace to be
  the open one. It now requires the person to still be a member of both the cookie's
  workspace and the open one, in one query. So switching in one tab switches the others,
  as accepted, instead of signing them out.
- **The web sign-up and Google sign-in match an existing email ignoring case.** That
  avoids two accounts differing only by case.
- **Opening a workspace answers with a new session token** for the frontend to set as the
  cookie. The New workspace dialog creates and then opens.
- **Frontend clean-up:**
  - Deleted with the old forms: the `react-hook-form` and `@hookform/resolvers` packages,
    the login, register and profile form schemas and types, and the `form`, `input` and
    `label` primitives.
  - Added `@radix-ui/react-dialog` and a dialog primitive.
  - New design tokens for the dialog: backdrop, shadow, and a 17px heading size (the
    design's dialog title; not in the original type scale).
- **The new forms do not use Zod with React Hook Form**, against `frontend/CLAUDE.md`
  (raised by `/code-review`, not changed). The design shows errors only after submit,
  each in one place, and plain state matched that more simply. A reviewer may ask for
  the convention.
- **Accounts marked GitHub** (never offered) become email accounts in the migration.
- **`docs-internal/deployment.md`** (merged from main while this was open) now lists the
  Google settings for the hosted services.

### Check results

`make check` on the final tree: see the table below (run after this Outcome was written).

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

`next build` passes. Sign-in, sign-up and the profile menu use only design tokens; the
Google mark keeps its own colours, as the design says.

New and updated backend tests:

- `test_workspaces.py` (8): sign-up workspace and its name, create, switch and scope, not
  a member, blank or long names, membership lost ends the session, ordering, an email
  differing only in case.
- `test_google_auth.py` (14): status, new email, known email, six refused ID tokens, five
  Google failures (timeout, error, empty, malformed, not a JWT), and a refusal or a forged
  or unbound state.
- `test_oauth.py` (15): the approval step on every path, Allow, Cancel, Allow without a
  session, "Not you?", sign-up errors under their field, a wrong password, an invalid
  email, and no framing.
- `test_mcp.py`: `create_workspace` and a blank name.
- MCP server tests: 17.

Migrations `0011_workspace_members` apply, reverse and re-apply on the local database,
with no drift. Every existing person became a member of their company.

**Played through on running servers** (backend on port 8001, MCP server on port 8012):

| # | Call | Came back |
|---|---|---|
| 1 | Sign up with a 7-character password, then 16 | 422, then 200 |
| 2 | Sign in | 200; one workspace, open, named "Bright Dental …" |
| 3 | Create an agent | Listed in the first workspace |
| 4 | Create "Kestrel Plumbing" | 200, not open; two workspaces |
| 5 | Open it | 200 with a new token; no agents; it is the open one |
| 6 | Open the first again | 200; the agent is back |
| 7 | `GET /auth/google` without settings | `{"enabled": false}` |
| 8 | Connection page: sign in | 200; approval page with Allow |
| 9 | Authorize again while signed in | 200; approval page |
| 10 | Cancel | 303 to the assistant with `error=access_denied&state=s` |
| 11 | Allow | 303 with a code; the code gives a token |
| 12 | "Not you?" | 200; sign-in form; session cookie cleared |
| 13 | MCP `list_workspaces`, `create_workspace` | 2, then 3 workspaces; the three tools listed |
| 14 | MCP `create_workspace` with a blank name | Error "A workspace needs a name." with a next step |
| 15 | Web open workspace after the MCP calls | Unchanged |

`/code-review` (high) raised eight findings. Fixed:

- the connection pages could be framed;
- web sign-up allowed an email differing only in case;
- sign-up could show a raw validation message;
- two membership queries per request.

Not fixed, listed below: the session token in the Google redirect URL, the forms
convention (above), a silent failure when opening a workspace, and Google Fonts on the
connection page.

**For Dmytro to check on screen**, against `Connexity Sign in.dc.html` and
`Connexity Sidebar.dc.html`, in dark and light:

1. `/register`:
   - create an account with a password under 8 characters (error under the field), then
     with an email already used (error under the email, "Sign in instead");
   - then a new one, which lands in the shell with "Bright Dental"-style workspace name
     under your name.
2. Sign out, then `/login`: a wrong password (one line above the button), then the right
   one.
3. The profile menu shows Workspaces with the open one ticked.
4. New workspace:
   - Create stays disabled while the name is empty, and over 255 characters an error
     shows;
   - Escape and a click outside cancel;
   - Create opens the new workspace, its name shows under yours, and the menu ticks it.
5. Switch back to the first workspace from the menu.
6. With 9 or more workspaces, the search field appears and filters the list.
7. Connect Claude Code to your local MCP server:
   - sign in on the connection page, see the approval page and press Allow;
   - try "Not you?";
   - try Cancel.
8. With `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` set (steps below), "Continue with
   Google" signs in and comes back to the shell. Without them the button and the "or"
   divider are absent.

### Not done

- **Google against the real Google:** tested with mocks only. To set it up:
  1. In Google Cloud, create an OAuth client of type "Web application".
  2. Add the redirect URI `<backend origin>/api/v1/auth/google/callback`, locally
     `http://localhost:8000/api/v1/auth/google/callback`.
  3. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
- **Google on the assistant-connection page** (see deviations).
- **The session token after Google sign-in travels in a URL**, the way the existing
  `/api/auth/set-cookie` route works. A one-time code would keep it out of logs and
  history; worth its own change.
- **Opening a workspace that fails** (removed, or the session expired) closes the menu
  without a message; the design has no state for it.
- **The connection pages load Figtree from Google Fonts**, not self-hosted.
- **The design files still draw the two-circle mark**; the build uses the three-loop
  logo.
- **Throwaway data in the local dev database:** two play-through users with four
  workspaces and two agents.
