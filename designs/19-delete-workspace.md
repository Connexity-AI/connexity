# 19. Deleting a workspace

Pasted into Claude Design on 2026-11-24. The result is
`screens/Connexity Workspaces.dc.html` (every state on one canvas), the `workspaces`
section and delete dialog of `screens/Connexity Agency.dc.html`,
`screens/Connexity Workspace Deleting.dc.html`, the `deleted` variant of
`screens/Connexity Email.dc.html` and the picker in `screens/Connexity Sidebar.dc.html`.
How it works: [`docs-internal/workspace-deletion.md`](../docs-internal/workspace-deletion.md).
Built: all six sections. Where the build differs from the design is listed in that
document under "Screens".

```txt
Add deleting a client workspace to Agency settings (Connexity Agency), in dark and light. Keep the existing layout and design system. Sentence case, plain words, no exclamation marks. One primary button per screen. Orange is only the logo.

## The rule
Deleting a workspace permanently removes its calls, recordings, transcripts and everything derived from them. It cannot be undone. Only an Admin who can approve can do it. An assistant can never do it alone: it can only send the person to this screen.

## 1. Workspaces section
Add a third section to Agency settings, after Members and Billing: "Workspaces". A simple table:
Workspace · Agents · Calls stored · Created · a quiet "⋯" menu.
- "Bright Dental · 3 agents · 4,120 calls · 12 Sep 2026"
- The ⋯ menu has "Delete workspace", in the critical colour.
- A person who can't delete sees the table without the ⋯ menu.

## 2. Delete dialog
A dialog on surface-2:
- Title: "Delete Bright Dental?"
- One line: "This permanently deletes the workspace and can't be undone."
- A short plain summary in tabular figures:
  - "4,120 calls with their recordings and transcripts"
  - "3 agents with their specs, scenarios and test runs"
  - "27 issues and their history"
- One muted line: "Its Retell connection is removed, so no new calls arrive. Your calls in Retell are not touched."
- One muted line: "Usage totals stay on your invoices, without any call content."
- A field: "Type Bright Dental to confirm" (the name in bold)
- Buttons: "Delete workspace" (critical, disabled until the name matches) and "Cancel".

## 3. While deleting
The row stays in the table, dimmed, with "Deleting…" and a thin progress line. People with this workspace open see a calm full-page line: "This workspace is being deleted." with a link to another workspace. It no longer appears in the workspace picker.

## 4. When it's done
- The row disappears, and a quiet line appears at the top of the section: "Bright Dental was deleted."
- The action stays in the agency's record: who deleted which workspace, and when. It holds no call content.
- If it fails: the row shows "Couldn't finish deleting" in the critical colour, with "Try again".

## 5. The last workspace
An agency's last workspace cannot be deleted. In its ⋯ menu "Delete workspace" is disabled, with the tooltip: "Create another workspace first. An agency needs at least one."

## 6. Confirmation email
A short plain email to the agency's Admins, with the logo:
- Subject: "Bright Dental was deleted from Connexity"
- "Alex Morgan deleted the workspace Bright Dental and its data on 23 Nov 2026."

## Show
- The Workspaces section, dark, desktop.
- The delete dialog, with the button disabled, and with the name typed.
- The row while deleting.
- The failed state.
- The last workspace's menu with the disabled item and its tooltip.
- The dialog in light and at phone width.
- The email.

## Avoid
- A soft-delete, trash or restore option.
- Any promise about how long backups are kept.
- Deleting from the sidebar or the profile menu.
- A button an assistant could press.
- Real client names: use Bright Dental and Alex.
```
