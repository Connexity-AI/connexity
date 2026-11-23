# Invites and Members screen (1 of 2): invites and Agency settings › Members

- **Owner:** Dmytro
- **Slice:** Invites and Members screen (roadmap Order 102.37), first of two pull
  requests. The second adds the profile menu grouped by agency and workspace Settings ›
  Team.
- **Design:** Claude Design project "Connexity", from the export Dmytro handed over on
  2026-11-23: `Connexity Agency Members` (every state on one canvas), the `members`
  section of `Connexity Agency`, the `invite` screens of `Connexity Sign in`, and the
  `invite` variant of `Connexity Email`. The export's `Connexity Agency`,
  `Connexity Agency Members` and `Connexity Sidebar` pages are copied into
  `designs/screens/` with this change, and the prompt becomes
  `designs/18-agency-members.md`.
- **MCP:** Four tools, each with its `contract.py` entry, a description for every
  input, and a new `people` guide:
  - `list_people` (reads): who is in the agency, their role, the workspaces each
    reaches, whether they can approve, and the invites waiting.
  - `invite_people`, `update_person`, `remove_person`: only for an assistant whose
    person is an Admin, and only after the person says yes (`needs_yes`).

## Goal

An agency can bring its people in and decide what each of them reaches, without anyone
touching the database. Today an agency has exactly the person who signed up: the rules
for roles and access exist (roadmap row "Agency account") but there is no invite and no
screen.

After this merges an Admin invites people by email from Agency settings › Members,
changes their role, workspaces and whether they can approve, and removes them; an
invited person joins from the email in every case the design covers; and a person who
cannot approve is refused the decisions that need it.

## Changes

### What a person sees (as designed)

1. **Profile menu:** "Agency settings" under the workspaces, opening the agency of the
   workspace that is open.
2. **Agency settings › Members** (`/agency`): the count ("6 people · 1 invited"), the
   table (Person, Role, Workspaces, Can approve, the "⋯" menu), "You" on the person's
   own row, invited people with the "Invited" chip and "Expires in 5 days", and the
   line saying what "can approve" allows. A Member sees the same table read only. The
   page shows Members only; Billing appears with the billing rows.
3. **Invite row:** emails (several, separated by commas), Role, Workspaces, Can approve,
   "Invite". States: invalid email, "sam@example.com is already in Signal Voice.",
   already invited, and "Invite sent to sam@example.com".
4. **Guard rails:** the last Admin's role and remove controls are disabled with the
   tooltip "An agency needs at least one Admin."; a person with no workspaces shows "No
   workspaces" in the warning colour.
5. **Remove dialog:** "Remove Sam Reyes?", with how many workspaces and connected
   assistants Sam loses, "Remove" and "Cancel".
6. **The invite email:** "Alex invited you to Signal Voice on Connexity", one button
   "Accept invite", "This invite expires in 7 days."
7. **Accept an invite** (`/invite/<token>`), in the sign-in layout:
   - no account: Continue with Google, or Name and Password with the email fixed,
     "Create account and join";
   - has an account, not signed in: the same title with Sign in;
   - signed in with the invited email: "You'll get access to 3 workspaces", "Join" and
     "Decline";
   - signed in with another email: "This invite is for … You're signed in as …", "Sign
     in with another account";
   - expired or cancelled: "This invite no longer works. Ask Alex for a new one."

### Backend

- **New table `agency_invite`:** the agency, the invited email, the role, the workspaces
  (all or chosen) and "can approve" the person will get, who invited them, when it was
  last sent, when it expires (7 days after the last send), and when it was accepted or
  cancelled. Only a hash of the link's token is stored.
- **Admin routes** under `/agencies/{id}/invites`: invite (one or several emails),
  resend (a new link, seven more days; the old link stops working) and cancel. An
  already-member and an already-invited email are refused with the designed sentence.
- **Accepting:** a public route says what a link is (agency, who invited, the email, how
  many workspaces) or that it no longer works; joining needs the invited email, as a
  signed-in session, a new account with that email, or Google sign-in that returns
  that email. A link works once.
- **A person who joins by invite gets no agency of their own.** They are a member of
  the agency that invited them, with exactly what the invite said.
- **"Can approve" is enforced** on the decisions that exist today from the design's list
  ("archive issues, close incidents, override the gate, and change the Playbook and
  checks"): archiving and unarchiving an issue, and changing a check's settings, on the
  web and through an assistant. The refusal says who in the agency can approve.
  Closing incidents, the gate and the Playbook get the same rule when they are built.
- **Email** goes through the sending built for password reset. A failed send is logged
  and the invite still exists, so "Resend invite" recovers it.

### Assistants

- `list_people` for anyone's assistant; the three changing tools for an Admin's
  assistant, after the person says yes. They call the same rules as the screen: the
  last Admin is protected, and a removed person's assistants lose access at once.
- A tool that records a decision as approved by the person (`archive_issue`,
  `unarchive_issue`) is refused when that person cannot approve.

### Docs

- `docs-internal/agency.md` (invites, accepting, what "can approve" gates),
  `data-model.md`, `decisions.md`, `mcp-architecture.md`; `docs/` for people outside.

## Decisions

1. **Decided (Dmytro, roadmap row and design, 2026-11-23):** invite by email, expiring
   in 7 days, with resend and cancel; every accept state; remove ends the person's and
   their assistants' access at once and keeps what they did on record; the last Admin
   is protected; the assistant can read who has access, and inviting, removing and
   changing access follow the approval rule; seats are free.
2. **Decided (Dmytro, the design's own sentence):** what "can approve" allows.
3. **Decided (Dmytro, 2026-11-23):** two pull requests, this one first.
4. **Decided (Dmytro, 2026-11-23):** a person who joins by invite gets only the
   inviting agency, no agency of their own.
5. **Decided (Dmytro, 2026-11-23):** anyone who reaches a workspace may answer the
   assistant's clarification questions; "can approve" gates archiving and unarchiving
   issues and changing checks for now.
6. **Decided (Dmytro, 2026-11-23):** four assistant tools: `list_people` for anyone's
   assistant, and `invite_people`, `update_person` and `remove_person` for an Admin's
   assistant, each only after the person says yes.
7. **Proposed:** an invite must give at least one workspace (all, or one or more
   chosen). "No workspaces" can only arise later, when an Admin narrows someone.
8. **Proposed:** a join needs the invited email; an invite cannot be forwarded to
   another address.
9. **Proposed:** resending makes a new link and restarts the seven days.

## Done when

- Route tests through the API on the local database:
  - invite one and several emails; the email is the designed one and is sent once per
    address; invalid, already a member and already invited are refused as designed;
  - only a hash of the link is stored; the link works once; it stops after 7 days;
    resend replaces it; cancel ends it;
  - each accept state: new account by password, existing account signed in, wrong
    email refused, expired and cancelled the same answer;
  - the person who joins has the invite's role, workspaces and "can approve", no agency
    of their own, and reaches the workspaces on the web and through an assistant;
  - a Member cannot invite, resend, cancel, change or remove;
  - a person who cannot approve is refused archiving, unarchiving and changing a check,
    on the web and through their assistant, and is told who can; a person who can is
    not;
  - the four assistant tools, including an assistant of a Member refused the three
    changing ones.
- MCP server tests, with contract entries and input descriptions.
- `make check` passes.
- For Dmytro to check on screen: the Members page as Admin and as Member, the invite
  states, the last-Admin tooltip, the remove dialog, the five accept screens and the
  email, in dark and light and at phone width, against the design.

## Out of scope

- **Second pull request of this row:** the profile menu grouped by agency for a person
  in several, and workspace Settings › Team.
- A sign-in message for a person with no workspace left: the design has no state for
  it. Password sign-in already answers with a plain sentence that the form does not
  show.
- Billing in Agency settings; seat counts; custom roles; client logins.
- Inviting someone to a single workspace from the workspace's own settings.
- Email verification for accounts made without an invite.

## Risks

- **The free email plan sends 100 emails a day.** A large invite list could use it up
  and password resets would then fail until the next day. Invites beyond the limit are
  kept and can be resent.
- **An invite gives access to clients' calls.** Joining is tied to the invited email;
  a reviewer should look first at the accept route and its tests.
- **Refusing decisions.** Everyone existing can approve, so nothing changes for them.
  A reviewer should check that no decision a person can make today is refused for
  someone who has the setting.

## Outcome

### Deviations from the plan

- **Controls come from what the app's UI kit has.** There is no select, switch or
  tooltip component yet, so Role and Workspaces are dropdown menus, "Can approve" is the
  design's checkbox with "Can approve" or "View only", and the last-Admin explanation is
  the browser's own tooltip on the disabled control, not the designed dark bubble.
- **A link that no longer works says "Ask the person who invited you for a new one."**
  The design says "Ask Alex for a new one.", but a dead link no longer tells who sent
  it.
- **"Already invited" reads "sam@example.com already has an invite."** The design names
  the state without wording it.
- **Declining** ends the invite and opens the app; the design does not say where it
  goes.
- **`remove_person` also cancels an invite** (by the invite's id from `list_people`),
  so the assistant can do what the invite's "⋯" menu does without a fifth tool.
  Re-inviting through the assistant after a cancel replaces "Resend invite".
- **`list_people` and its siblings take a `workspace_id`** and act on that workspace's
  agency, like every other tool.
- **Agency settings shows the agency of the open workspace** and has one section,
  Members. Renaming the agency has a route but no control: the design has none.
- **Members with assistants:** the count of a person's connected assistants in the
  remove dialog is personal access tokens that were used and still work, plus OAuth
  connections that can still refresh.
- **Continue with Google on the invite page** is built (the invite travels through
  Google sign-in), but Google sign-in is off in production and it has no test here.
- **A fourth invite route, `POST /invites/{token}/signin`** (from the code review): it
  checks the password of the invited email's account and joins in one request. The plan
  had the page sign in through the ordinary sign-in and then accept, which refuses a
  person with no workspace left.
- **Invited by email on the web form: several addresses** may be separated by commas or
  spaces.

### Check results

Route tests through the API on the local database (`TestClient`; no separate
play-through server, the tests send the same requests, as a web session and as an
assistant with a personal access token):

| What | Result |
|---|---|
| `test_invites.py` (14 tests): the designed email once per address; invalid, already a member and already invited come back with their sentence; an invite needs one of the agency's workspaces; only a hash of the link is stored; a Member cannot invite, resend or cancel and sees no invites; resend replaces the link, cancel ends it, the address can be invited again; the link stops after 7 days and an unknown link is the same 404; a new person joins with the invite's role, workspaces and "can approve", no agency of their own, on the web and through an assistant, and the link works once; an existing account joins signed in and keeps its own agency; a person removed and invited again is refused by the ordinary sign-in and joins by signing in from the invite; another email cannot accept or decline (403) and the invited person can decline; a person who cannot approve is refused archiving and unarchiving, on the web and through their assistant, is told who can, and may still resolve; an Admin's assistant invites, lists, changes, cancels and removes, with the last Admin protected; a Member's assistant reads and changes nothing | passed |
| Whole backend suite, before the review fixes | passed (1,106 tests) |
| MCP server tests, with the four tools, contract entries, the group and the guide | passed (65) |
| Backend `ruff` and `pyright`; frontend types and lint; generated client regenerated | passed |
| Full `make check`, after the review fixes | passed, every step |

For Dmytro to check on screen (local run with the Resend settings; dark, light and phone
width, against `designs/screens/Connexity Agency Members.dc.html`):

1. Profile menu: "Agency settings" under "New workspace" opens `/agency`.
2. Members as Admin: the count line, your row marked "You", Role, Workspaces and Can
   approve editable, and the sentence about approving under the table.
3. As the only Admin, your Role and "Remove from agency" are disabled, with "An agency
   needs at least one Admin." on hover.
4. Invite two addresses separated by a comma: "Invite sent to …", both rows appear with
   "Invited" and "Expires in 7 days". Invite "sam@example", yourself and one of them
   again: three sentences under the row.
5. The email: "Alex invited you to … on Connexity", "Accept invite", the 7-day line.
6. The invite link in a private window: "Join …", Name, the email fixed, Password,
   "Create account and join" opens the app in that agency. An address that has an
   account shows Sign in with "Forgot password?".
7. The link while signed in as someone else: "This invite is for … You're signed in as
   …", and "Sign in with another account" returns to the invite signed out.
8. Resend from the "⋯" menu, then the first link: "This invite no longer works".
9. As the new Member: the same table read only, no invite row; archiving an issue is
   refused with who can approve.
10. Back as Admin: "Remove from agency" opens "Remove …?" with the workspaces and
    assistants lost; after Remove the row is gone.

### Code review

Three findings, all fixed:

- A person removed from an agency and invited again could not join: the ordinary
  sign-in refuses an account with no workspace left. Now the invite signs them in and
  joins in one request, with a test.
- An existing account could join through an invite whose workspaces no longer exist and
  become a member who reaches nothing. Now it gets "This invite no longer works", as
  sign-up already did.
- Signing in from the invite page failed for an account whose stored email has capital
  letters. The account is now found ignoring case.

### Not done

- No invite email was sent through the real provider in this change; sending is tested
  up to the hand-over to SMTP, with the template checked for its wording.
- The screens were not opened in a browser; that is Dmytro's check above.
- Continue with Google through an invite is untested.
- The designed tooltip bubble (see Deviations).
