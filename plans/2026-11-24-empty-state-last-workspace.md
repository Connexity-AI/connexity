# Empty state after the last workspace

- **Owner:** Dmytro
- **Slice:** Empty state after the last workspace (roadmap Order 102.57), one pull
  request, built after the design export.
- **Design:** Claude Design project "Connexity", from the export Dmytro handed over on
  2026-11-24 (the second of two that day, which he named the latest): the "No
  workspaces yet" state and the delete dialog's line for the last workspace in
  `Connexity Agency`, the profile menu with "No workspace" in `Connexity Sidebar`, and
  the updated canvas `Connexity Workspaces`. These three pages are copied into
  `designs/screens/` with this change and the prompt becomes
  `designs/22-no-workspaces.md`.
- **MCP:** no new tool. `list_workspaces` answers an empty list with what to do next,
  `create_workspace` works with no workspace open, and `prepare_workspace_deletion`
  no longer says the last workspace cannot be deleted. Contract text updated.
- **Status:** Approved by Dmytro ("Accept, build", 2026-11-24).

## Goal

An agency can delete its last client workspace and still use Connexity: the Admin signs
in, sees that there are no workspaces, creates the next one, and reaches Agency settings
meanwhile. Today the last workspace cannot be deleted at all, because every account
must have a workspace open.

## What the code is today

- **Every account has an open workspace** (`user.company_id` is required).
- **Sign-in refuses a person who reaches no workspace,** with "You no longer have access
  to any workspace."
- **A session is tied to a workspace** and every request checks the person still
  reaches the one they have open.
- **56 web routes and 39 assistant routes read the open workspace.** Routes about the
  person, their agencies and billing do not.
- **Deleting an agency's last workspace is refused** in the route, the screen (a
  disabled item with a tooltip) and the assistant tool.
- **Agency settings finds its agency through the open workspace,** so it cannot open
  without one.

## Changes

### Backend

- **Signing in with no workspace:** allowed for a person who is an Admin of an agency.
  A Member who reaches no workspace is refused as today.
- **A session with no workspace open:** routes that need a workspace answer 409 "No
  workspace is open." Routes about the person, their agencies, Agency settings and
  creating a workspace work.
- **Creating a workspace with none open** puts it in the agency the person is an Admin
  of, opens it and gives them a normal session. A person who is an Admin of several
  agencies says which.
- **Deleting the last workspace is allowed,** by the same rule as any other (an Admin
  who can approve, the name typed). The person who deleted it has no workspace open
  afterwards.
- **The subscription is not touched:** an agency with no workspace keeps its
  subscription and balance until an Admin cancels.

### What a person sees (from the design)

- **No workspaces:** in place of the app, "No workspaces yet" with the primary button
  "New workspace", which opens the existing dialog.
- **Agency settings, Account and Sign out** stay reachable from the profile menu.
- **The delete dialog for the last workspace** says that it is the agency's last one.
- **The disabled "Delete workspace" item and its tooltip go.**

### Assistants

- **`list_workspaces`** with none: an empty list, and the step to create one (for an
  Admin) or to ask an Admin.
- **`create_workspace`** works with no workspace open.
- **`prepare_workspace_deletion`** says when a workspace is the agency's last, as a
  fact to tell the person, no longer as a refusal.

### Docs

- `docs-internal/agency.md`, `workspace-deletion.md`, `mcp-architecture.md`,
  `designs/README.md`, `designs/22-no-workspaces.md`.

## Decisions

- **Decided (Dmytro, 2026-11-24, roadmap row):** the app works with no open workspace;
  the "No workspaces yet" state with "New workspace"; sign-in for an Admin whose agency
  has no workspace; then deleting the last workspace is allowed.
- **Decided (Dmytro, 2026-11-24):** only Admins are let in with no workspace; a Member
  who reaches none is refused at sign-in as today.
- **Decided (Dmytro, 2026-11-24):** with no workspace an Admin reaches "New workspace"
  and Agency settings (Members, Billing, Workspaces), Account and Sign out.
- **Decided (Dmytro, 2026-11-24):** the subscription keeps running, and the delete
  dialog says so for the last workspace: "This is your agency's last workspace. Your
  subscription keeps running until you cancel it."
- **Decided (Dmytro, 2026-11-24):** one pull request, backend and screens together,
  built after he hands over the design export ("just give me design prompt and
  wait").

## Done when

- Through the API on the local database: an Admin deletes the agency's only workspace;
  signs in again and is let in; workspace routes answer 409 and agency, billing and
  account routes work; creating a workspace opens it and everything works again; a
  Member with no workspace is still refused at sign-in; an assistant lists no
  workspaces and can create one for an Admin.
- MCP server tests pass with the changed texts.
- Frontend types and lint pass; the full `make check` passes.
- On screen (Dmytro): every state of the new design.

## Out of scope

- Deleting an agency, or a person's account.
- A Member with no workspace seeing anything but the sign-in refusal (see the question).
- Cancelling the subscription automatically when the last workspace goes.

## Risks

- **This touches sign-in and the session check for everyone.** The change is limited to
  people who reach no workspace, with tests that everyone else is treated as before.
- **A page that forgets to handle "no workspace open"** would show an error. The app
  shell shows the empty state before any page loads, so pages are not reached.

## Outcome

### A test whose expectation changed

`test_losing_membership_of_the_open_workspace_ends_the_session` in `test_workspaces.py`
expected a 401 for a person who loses their open workspace. That person was an Admin,
and an Admin who reaches no workspace is now let in with none open (Decided by Dmytro,
2026-11-24). The test became two: a Member is still signed out (401), and an Admin
stays in and workspace routes answer 409. Nothing was loosened: the old case is kept
for the people it still applies to.

### Deviations from the plan

- **Creating a workspace with none open also opens it,** in the same request. Without
  that the person's session was refused in the moment between creating the workspace
  and opening it, because they then reached a workspace that was not the one open.
- **The pages that show one workspace moved into a route group,**
  `app/(app)/(workspace)`: Work, Dashboard, Agents, Calls and Issues. Their addresses
  did not change. The group's layout shows "No workspaces yet"; Agency settings and
  Account stay outside it.
- **Dashboard and Readiness now use the shared workspace check.** They read the open
  workspace straight from the person and would have answered an empty page for a
  deleted workspace instead of "No workspace is open."
- **An assistant's connection survives its person's last workspace being deleted.**
  Before, a connection whose person reached no other workspace was removed with the
  workspace. The row holds no call content and now stays.
- **An Admin of several agencies with no workspace** is asked which agency on the API
  ("Say which agency the workspace is for."). The "New workspace" dialog has no agency
  picker, so such a person creates the workspace through their assistant, or after
  opening Agency settings of the other agency. The design has no state for this.
- **"Who is let in" is decided by being an Admin of any agency,** not of the agency
  whose workspace was deleted.

### Check results

Route tests through the API on the local database (`TestClient`; no separate
play-through server):

| What | Result |
|---|---|
| `test_workspace_deletion.py` (three new tests, one replaced): an Admin deletes the agency's only workspace and the same session goes on with no workspace open; workspace routes answer 409 with the sentence and agency routes work; the Workspaces table is empty with its Record; signing in again lets the Admin in; their assistant is still connected, lists nothing and is told to create a workspace; creating one needs no agency named, opens it, and the app's routes work again; a Member whose only workspace is deleted is signed out, refused at sign-in and cannot create a workspace through an assistant; an Admin of two agencies with no workspace is asked which and can say; the assistant's `prepare_workspace_deletion` reports the last workspace as a fact with what follows | passed |
| Agency, invite, sign-in, Readiness and Dashboard tests | passed |
| MCP server tests | passed |
| Backend `ruff` and `pyright`; frontend types, lint and formatting; client regenerated | passed |
| Full `make check` | First run: one test failed, the one described above under "A test whose expectation changed". After updating it: passed, every step |

For Dmytro to check on screen (dark, light and phone width, against
`designs/screens/Connexity Workspaces.dc.html` and the "No workspaces yet" state in
`Connexity Agency`), with a test agency that has one workspace:

1. Agency settings, Workspaces: the only workspace's menu has "Delete workspace" in the
   critical colour; the dialog has the extra line about the last workspace and the
   subscription.
2. Delete it: the app shows "No workspaces yet" with "New workspace"; the sidebar has
   only the logo and the profile menu, which reads "No workspace" under your name.
3. From the profile menu: Agency settings opens, its header reads "… · No workspaces",
   Workspaces shows "No workspaces yet" and the Record line; Account opens.
4. Any workspace page by its address (for example `/calls/`) shows "No workspaces yet".
5. "New workspace": after creating, the app opens that workspace and every page is
   back.
6. Sign out and in again while there is no workspace: you are let in.

### Code review

Two findings:

- **Fixed:** a failed read of the workspace list was treated as an empty list, so a
  person with workspaces could be shown "No workspaces yet" and invited to create one.
  The empty state now shows only when the list was read and is empty.
- **Left:** each request to a workspace route asks the database once more whether the
  person reaches their open workspace, a question the session check has just asked. It
  is one indexed query; carrying the first answer along is a small follow-up.

### Not done

- The screens were not opened in a browser; that is the list above.
- An agency picker in the "New workspace" dialog for an Admin of several agencies (see
  Deviations).
- No frontend test: the app has none.
