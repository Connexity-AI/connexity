# 22. An agency with no workspaces

Pasted into Claude Design on 2026-11-24. The result is the "No workspaces yet" state
and the delete dialog's line for the last workspace in
`screens/Connexity Agency.dc.html`, the profile menu with "No workspace" in
`screens/Connexity Sidebar.dc.html`, and the updated canvas
`screens/Connexity Workspaces.dc.html`. How it works:
[`docs-internal/agency.md`](../docs-internal/agency.md), "With no workspace". Built: all
four sections.

```txt
Add what an agency sees when it has no workspaces (Connexity Agency, Connexity Sidebar, Connexity Workspaces), in dark and light. Keep the existing layout and design system. Sentence case, plain words, no exclamation marks. One primary button per screen. Orange is only the logo.

## The rule
An agency can delete its last client workspace. Its Admins can still sign in, create the next workspace, and reach Agency settings. A Member who reaches no workspace cannot sign in, so there is no screen for them. The subscription keeps running until an Admin cancels it.

## 1. No workspaces yet
What an Admin sees after signing in, or right after deleting the last workspace, in place of the app's pages:
- The sidebar stays, with only the logo at the top and the profile menu at the bottom. No page links, no Readiness ring.
- In the page area, centred and calm: the title "No workspaces yet", one muted line "Create a workspace for a client to start checking their calls.", and the primary button "New workspace".
- "New workspace" opens the existing New workspace dialog. After creating, the app opens that workspace.

## 2. Profile menu with no workspaces
The same menu as today, with the Workspaces part reduced to "New workspace" and "Agency settings". No workspace list and no search. Account, Theme and Sign out are unchanged. Under the person's name, in place of the workspace name, the muted line "No workspace".

## 3. Agency settings with no workspaces
Members, Billing and Workspaces open as they do today.
- The header line reads "Signal Voice · No workspaces".
- Workspaces shows an empty table state: "No workspaces yet", with the Record list of deleted workspaces under it as today.
- Members: a person's Workspaces column shows "No workspaces" in the muted colour, not the warning colour, because the agency has none to give.

## 4. Deleting the last workspace
Update the delete dialog in Connexity Workspaces:
- The last workspace's menu has "Delete workspace" in the critical colour, like any other. Remove the disabled item and its tooltip "Create another workspace first. An agency needs at least one."
- When it is the agency's last workspace, the dialog adds one muted line under the usage line: "This is your agency's last workspace. Your subscription keeps running until you cancel it."
- After it is deleted, the app shows "No workspaces yet" (section 1).

## Show
- "No workspaces yet", dark, desktop.
- The profile menu open in that state.
- Agency settings, Workspaces, with no workspaces and one line in the Record.
- The delete dialog for the last workspace, with the name typed.
- "No workspaces yet" in light, and at phone width.

## Avoid
- A screen for Members with no workspace: they are refused at sign-in.
- Any promise that the subscription is cancelled or paused.
- Sample data, illustrations or a checklist in the empty state.
- Real client names: use Signal Voice, Bright Dental and Alex.
```
