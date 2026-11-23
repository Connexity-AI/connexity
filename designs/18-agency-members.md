# 18. Agency members, invites and accepting

Pasted into Claude Design on 2026-11-23, on top of item 24 in
[`12-adjustments.md`](./12-adjustments.md). The result is
`screens/Connexity Agency Members.dc.html` (every state on one canvas), the `members`
section of `screens/Connexity Agency.dc.html`, the `invite` screens of
`screens/Connexity Sign in.dc.html`, the `invite` variant of
`screens/Connexity Email.dc.html` and the two-agency profile menu in
`screens/Connexity Sidebar.dc.html`. How it works:
[`docs-internal/agency.md`](../docs-internal/agency.md). Built: sections 1 to 7.
Section 8 (workspace Settings › Team) is built with the roadmap row "Settings: team",
which also brings the workspace Settings page (Decided by Dmytro, 2026-11-23).

```txt
Update Agency settings › Members (Connexity Agency) and add the screens around it, in dark and light. Keep the existing layout, table and invite row. Use the existing design system. Sentence case, plain words, no exclamation marks. One primary button per screen. Orange is only the logo. The Billing section is not part of this prompt: leave it as it is.

## The model
An agency has many client workspaces and many people. Each person has:
- Workspaces: All, or chosen ones.
- Can approve: may make the critical decisions in those workspaces.
- Role: Admin or Member. Admins manage people and billing. Members only work in their workspaces.
A person's AI assistants reach exactly the workspaces that person can reach. Clients never log in.

## 1. Members table
Columns: Person · Role · Workspaces · Can approve · a quiet "⋯" menu at the row's end. The email stays as a muted second line under the name.
- Role: a small inline select, Admin or Member.
- Workspaces: the existing picker ("All workspaces", "3 workspaces").
- Can approve: the existing switch.
- A muted count above the table: "6 people · 1 invited".
- The person's own row is marked "You".
- Invited people show a muted "Invited" chip and "Expires in 5 days" in place of the second line. Their ⋯ menu has Resend invite and Cancel invite.
- Other people's ⋯ menu has Remove from agency.

A Member sees the same table read only: no invite row, selects, switches or ⋯ menus.

## 2. Invite
Keep the existing invite row: email, Role, Workspaces, Can approve, and the primary button "Invite". Allow several emails, separated by commas.
States: invalid email, already a member, already invited, invite sent (a quiet line "Invite sent to sam@example.com").

## 3. Guard rails
- The last Admin cannot be removed or changed to Member. The control is disabled with a tooltip: "An agency needs at least one Admin."
- A person with no workspaces shows "No workspaces" in the warning colour.

## 4. Remove someone
A small dialog on surface-2:
- Title: "Remove Sam Reyes?"
- "Sam loses access to all 6 workspaces right away. Sam's 2 connected assistants stop reaching them too. What Sam did stays on record."
- Buttons: "Remove" (critical) and "Cancel".

## 5. The invite email
Plain and light, with the logo and "Connexity":
- Subject: "Alex invited you to Signal Voice on Connexity"
- "Alex Morgan invited you to work on 3 client workspaces at Signal Voice."
- One button: "Accept invite"
- Muted: "This invite expires in 7 days."

## 6. Accept an invite
Use the Sign in layout: one centred column about 360px wide.
- Not signed in, no account: title "Join Signal Voice", the muted line "Alex Morgan invited sam@example.com", Continue with Google, then Name and Password with the email fixed, and the primary button "Create account and join".
- Not signed in, has an account: the same title with Sign in.
- Signed in with the invited email: title "Join Signal Voice", "You'll get access to 3 workspaces", primary "Join", secondary "Decline".
- Signed in with another email: "This invite is for sam@example.com. You're signed in as alex@example.com." with the primary button "Sign in with another account".
- Expired or cancelled: "This invite no longer works. Ask Alex for a new one."

## 7. Profile menu with more than one agency
A person can belong to more than one agency. When they do, the Workspaces part of the profile menu groups workspaces under small muted agency names, and "Agency settings" opens the agency of the current workspace. With one agency, the menu stays exactly as it is today.

## 8. Workspace Settings › Team
Read only: the people with access to this workspace, with their role and whether they can approve, plus the assistants that reach it ("Claude Code · Alex"). One link: "Manage in Agency settings". Members do not see the link.

## Show
- Members table as an Admin, dark, with one invited person and the invite row.
- The same table as a Member, read only.
- The remove dialog.
- The last-Admin tooltip.
- Accept invite: new account, and the wrong-email state.
- The invite email.
- The profile menu with two agencies.
- Workspace Settings › Team.
- Members table in light, and at phone width with Role, Workspaces and Can approve folded under each name.

## Avoid
- Client logins, custom roles or a permissions matrix.
- Seat counts or seat prices: seats are free.
- A view across all workspaces.
- Any new item in the sidebar.
- Real names: use Alex, Sam and the agency "Signal Voice".
```
