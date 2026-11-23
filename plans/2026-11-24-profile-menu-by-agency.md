# Invites and Members screen (2 of 2): the profile menu grouped by agency

- **Owner:** Dmytro
- **Slice:** Invites and Members screen (roadmap Order 102.37), second and last pull
  request. The first (pull request 261) brought invites, Agency settings › Members and
  "can approve".
- **Design:** `designs/screens/Connexity Sidebar.dc.html`, the profile menu with
  `agencies` set to 2, and section 7 of `designs/18-agency-members.md`. Both are in the
  repo since pull request 261; the design does not change.
- **MCP:** No change. `list_workspaces` already names each workspace's agency, the
  person's role in it and whether they can approve.
- **Status:** Approved by Dmytro ("Accept, build").

## Goal

A person who belongs to more than one agency (their own, plus one they were invited to)
sees their workspaces grouped under the agencies' names in the profile menu, so two
workspaces with similar names in different agencies cannot be confused. A person in one
agency sees the menu exactly as it is today.

## Changes

### What a person sees (as designed)

- **More than one agency:** under "Workspaces", each agency's name is a small muted line
  and its workspaces follow it. The agency of the open workspace comes first; the others
  follow by name. The open workspace keeps its check mark.
- **Search** (from 9 workspaces, counted over all agencies) filters inside the groups; a
  group with no match disappears.
- **"New workspace" and "Agency settings"** stay where they are and act on the agency of
  the open workspace, as they do now.
- **One agency:** no agency name, no other change.

### Frontend

- `components/shell/profile-menu.tsx`: group `workspaces` by `agency_id` when they come
  from more than one agency, with the group label from `agency_name`. The grouping is a
  small pure function next to the component.

### Backend

- No route or model change: `GET /workspaces` already returns `agency_id` and
  `agency_name` for each workspace.
- One route test, if none covers it yet: a person in two agencies gets each workspace
  with its own agency's id and name.

### Docs

- `docs-internal/agency.md`: one sentence on the grouped menu.
- `designs/18-agency-members.md`: "Built so far" becomes sections 1 to 7; section 8
  (workspace Settings › Team) is named as the roadmap row "Settings: team".

## Decisions

- **Decided (Dmytro, 2026-11-23):** workspace Settings › Team is not part of this row.
  It is built with the roadmap row "Settings: team" (Order 132), which also brings the
  workspace Settings page; the app has none today.
- **Proposed:** the open workspace's agency is listed first, the others by name. The
  design shows the current agency first and does not say how further ones are ordered.

## Done when

- A person in two agencies sees two labelled groups, the open workspace's agency first,
  and opening a workspace of the other agency moves that agency to the top.
- A person in one agency sees no agency name.
- Search hides a group that has no matching workspace.
- Frontend types and lint pass; the route test passes; the full `make check` passes.

## Out of scope

- Workspace Settings › Team and the Settings page (row "Settings: team", Order 132).
- A sign-in message for a person with no workspace left.
- Choosing the agency in the "New workspace" dialog.

## Risks

- **The app has no frontend tests,** so the grouping is checked by types, lint and
  Dmytro on screen. Keeping it a pure function limits what can go wrong.

## Outcome

### Deviations from the plan

- **No new route test file:** the check that the workspace list names each workspace's
  own agency was added to the existing test of a person who joins a second agency
  (`test_a_person_with_an_account_joins_signed_in_and_keeps_their_own_agency`).
- **Searching keeps the agencies' order:** the order comes from all workspaces, not the
  filtered ones, so typing never moves a group.

### Check results

| What | Result |
|---|---|
| `test_invites.py` (14 tests), with the two-agency workspace list | passed |
| Frontend types, lint and formatting | passed |
| Full `make check`, after the review fix | passed, every step |

For Dmytro to check on screen, against `designs/screens/Connexity Sidebar.dc.html` with
two agencies:

1. As a person in one agency: the profile menu is unchanged, no agency name.
2. As a person in two agencies (accept an invite with an account that has its own):
   two muted agency names, the open workspace's agency first.
3. Open a workspace of the other agency: that agency moves to the top.
4. With 9 or more workspaces: search filters inside the groups and a group with no
   match disappears.

### Code review

One finding, fixed: with one agency the menu still announced an agency group to a
screen reader. The group and its label now exist only when the menu is grouped.

### Not done

- The menu was not opened in a browser; that is Dmytro's check above.
- No frontend test: the app has none.
