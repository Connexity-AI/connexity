# Delete workspace data (2 of 2): Agency settings › Workspaces and the assistant tool

- **Owner:** Dmytro
- **Slice:** Delete workspace data (roadmap Order 102.38), second and last pull request.
  The first brought the deletion, its record, the routes and the email.
- **Design:** Claude Design project "Connexity", from the export Dmytro handed over on
  2026-11-24: `Connexity Workspaces` (every state on one canvas), the `workspaces`
  section and delete dialog of `Connexity Agency`, `Connexity Workspace Deleting`, the
  `deleted` variant of `Connexity Email`, and the picker in `Connexity Sidebar`. These
  five pages are copied into `designs/screens/` with this change and the prompt becomes
  `designs/19-delete-workspace.md`.
- **MCP:** one new tool, `prepare_workspace_deletion`, with its `contract.py` entry, a
  description for its input, and guide text. No tool deletes.
- **Status:** Approved by Dmytro ("Accept, build", 2026-11-24).

## Goal

An Admin who can approve deletes a client workspace from Agency settings, sees what will
be removed before confirming, and sees afterwards that it is gone and who deleted it. An
assistant asked to delete a workspace can say what it would remove and send the person
to that screen.

## Changes

### What a person sees (as designed)

- **Agency settings gets a second section, Workspaces,** next to Members (Billing is not
  built, so it is not in the menu). The table: Workspace, Agents, Calls stored, Created,
  and a "⋯" menu with "Delete workspace" in the critical colour. At phone width the
  numbers fold under the name.
- **A person who cannot delete** sees the table without the menu. Under the table: "Only
  Admins who can approve can delete a workspace. An assistant can't delete one: it can
  only send you here."
- **The delete dialog:** "Delete Bright Dental?", the line that it cannot be undone, the
  three counts (calls, agents, issues), the two muted lines about the connection and
  usage totals, the field "Type Bright Dental to confirm", and "Delete workspace"
  disabled until the name matches.
- **While deleting:** the row is dimmed with "Deleting…" and a thin line.
- **Done:** the row disappears, "Bright Dental was deleted." shows at the top, and the
  Record list under the table gains "Alex Morgan deleted Bright Dental" with the date
  and time.
- **Failed:** the row shows "Couldn't finish deleting." with "Try again".
- **The last workspace:** "Delete workspace" is disabled, with the designed tooltip
  "Create another workspace first. An agency needs at least one."
- **A person who had the deleted workspace open** sees the full page "This workspace is
  being deleted." with "Go to <another workspace>" (see Decisions).

### Frontend

- `app/(app)/agency/page.tsx`: the section menu (Members, Workspaces) on
  `?section=workspaces`.
- New `components/agency/workspaces-view.tsx` (table, menu, dialog, record) and actions
  in `actions/agency.ts` for the table, the preview, delete and retry.
- The full-page line in the app layout, for a session whose workspace was deleted.

### Backend

- **The connection line names the platform:** the preview already returns the connected
  platforms; the dialog says "Its Retell connection is removed…" only when there is
  one, and leaves the line out when the workspace has no connection.
- **A session whose workspace was deleted stays valid** when its person still reaches
  another workspace (today it is refused and the person lands on sign-in). `GET
  /users/me` says so, so the layout can show the full-page line. Opening another
  workspace issues a normal session.

### Assistants

- **`prepare_workspace_deletion(workspace_id)`:** answers the workspace's name, what a
  deletion removes (calls, agents, issues, connections), whether the person the
  assistant acts for can delete it and who can, whether it is the agency's last
  workspace, and the address of Agency settings › Workspaces. Rules in the answer: it
  cannot be undone, only the person deletes, on that screen. It deletes nothing.
- Contract entry, input description, a section in the people guide, tests.

### Docs

- `docs-internal/workspace-deletion.md` (screens, the session rule, the tool),
  `mcp-architecture.md`, `designs/README.md`, `designs/19-delete-workspace.md`.

## Decisions

- **Decided (Dmytro, 2026-11-24, with part 1):** the last workspace cannot be deleted;
  backend first, screens from the design.
- **Proposed:** the thin line while deleting moves without a percentage. The design
  shows 38%, but a deletion runs in one request and has no real percentage to show.
- **Proposed:** the designed tooltip bubble is built for the disabled "Delete workspace"
  item (the UI kit has no tooltip; this adds a small one in the agency components).
- **Proposed:** the "deleted" line at the top shows until the page is left; the Record
  list is the lasting trace.
- **Decided (Dmytro, 2026-11-24):** a person who had the deleted workspace open sees
  the designed full page with a link to another workspace; their session keeps working
  when they still reach one.

## Done when

- Through the API on the local database: the tool answers the counts and who can
  delete, for an Admin's and a Member's assistant, and deletes nothing; a session whose
  workspace was deleted still works for a person with another workspace and is refused
  for a person with none.
- MCP server tests pass with the new tool, its contract entry and guide.
- Frontend types and lint pass; the full `make check` passes.
- On screen (Dmytro): every state on the `Connexity Workspaces` canvas.

## Out of scope

- The empty state after the last workspace; Billing in the section menu.
- Deleting from the sidebar or profile menu; restore or trash.
- Moving the deletion to the background.

## Risks

- **A delete button is the most dangerous control in the app.** It stays behind the
  typed name, the approve rule on the server, and a server-side check that the name
  matches; the screen never decides who may delete.
- **The session rule change touches sign-in for everyone.** It is limited to sessions
  whose workspace has `deleted_at` set, with tests for the other cases staying refused.

## Outcome

### Deviations from the plan

- **`GET /users/me` did not change.** The app layout reads the workspace the session
  was opened in from the session cookie, for display only, and shows the full page when
  that workspace is no longer in the person's list. The server still checks the session
  on every request.
- **The person who deletes gets a session in their open workspace right away.** Without
  it, an Admin who deleted the workspace they were in would see the full page meant for
  everyone else instead of "Bright Dental was deleted."
- **The full page says "This workspace is being deleted."** as designed, although by the
  time anyone sees it the deletion has finished: a deletion runs inside one request.
- **The line while deleting pulses, with no percentage** (Proposed in the plan).
- **The connection line lists every connected platform** ("Its Retell and n8n
  connections are removed…") and is left out when the workspace has none.
- **The tool's guide text is a section of the people guide,** not a new guide.
- **This branch was built on part 1's branch** while pull request 263 was open, and
  `main` was merged in after 263 merged; it now differs from `main` by this change only.

### Check results

Route tests through the API on the local database (`TestClient`; no separate
play-through server):

| What | Result |
|---|---|
| `test_workspace_deletion.py` (9 tests; three new): a session opened in a workspace that is then deleted goes on for a person with another workspace, is refused for a person with none, and a person removed from a workspace that still exists is still signed out; the assistant's tool answers the counts, the connections, who can delete and where, for an Admin's and a Member's assistant, says when it is the last workspace, and removes nothing; a deletion left running by a dead request is left alone at first, counts as failed after five minutes and finishes on "Try again" | passed |
| Agency, invite and sign-in tests | passed |
| MCP server tests (66), with the tool, its contract entry and the tool list | passed |
| Backend `ruff` and `pyright`; frontend types, lint and formatting; client regenerated | passed |
| Full `make check`, after the review fixes | every code step passed. The plan step failed while the branch sat on part 1's unmerged branch and carried two plans; after part 1 merged and `main` was brought in (no other change), the plan check was run again: passed |

For Dmytro to check on screen (dark, light and phone width, against
`designs/screens/Connexity Workspaces.dc.html`), in an agency with two workspaces:

1. Agency settings: the menu shows Members and Workspaces; Workspaces lists each
   workspace with agents, calls stored and created.
2. As an Admin who can approve: "⋯" has "Delete workspace" in the critical colour.
   As anyone else: no "⋯".
3. The dialog: the three counts, the connection line naming the platform (none when
   not connected), the usage line, and "Delete workspace" disabled until the name is
   typed exactly.
4. Delete: the row dims with "Deleting…", then disappears; "… was deleted." shows at
   the top and the Record list gains the line with your name, the date and time.
5. With one workspace left: "Delete workspace" is disabled and shows "Create another
   workspace first. An agency needs at least one." on hover or focus.
6. In a second browser signed in as someone who has the workspace open, before
   deleting: after the deletion their next page shows "This workspace is being
   deleted." and "Go to …" opens the other workspace.
7. The email "… was deleted from Connexity" arrives for each Admin.
8. Ask your assistant to delete a workspace: it calls `prepare_workspace_deletion`,
   says what would be removed and sends you to the screen.

### Code review

Three findings, all fixed:

- A deletion whose request died midway stayed "Deleting…" for ever, because only a
  failed deletion could be tried again. One still marked as running after five minutes
  now counts as failed, on the table and for "Try again", with a test.
- The explanation on the last workspace's disabled "Delete workspace" could not be
  reached with the keyboard. It is now a menu item that can be highlighted and does
  nothing, and the tooltip shows while it is highlighted.
- Dates and the Record's time were formatted in the server's time zone first and the
  browser's after; those spans are now allowed to differ.

### Not done

- The screens were not opened in a browser; that is the list above.
- The failed row with "Try again" is built and its route is tested, but a failure
  cannot be produced on screen without breaking the database on purpose.
- No frontend test: the app has none.
