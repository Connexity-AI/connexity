# Agencies

An agency is the thin account above its client workspaces. It owns the people and,
later, the billing. Clients never log in. Plan:
[`plans/2026-11-23-agency-account.md`](../plans/2026-11-23-agency-account.md). The
screens for people and invites are the roadmap row "Invites and Members screen".

## The model

- **`agency`:** a name. Every workspace (`company.agency_id`) belongs to exactly one.
- **`agency_member`:** a person in an agency, with
  - `role`: `admin` manages people and billing and creates workspaces; `member` works
    in their workspaces;
  - `all_workspaces`: reaches every workspace of the agency, including ones created
    later; when off, the person reaches the workspaces chosen for them;
  - `can_approve`: may make the critical decisions in their workspaces. Stored and
    returned today; refusing actions without it arrives with invites (Decided by Dmytro,
    2026-11-23), the first moment a person without it can exist.
- A person can be in more than one agency. Agencies share nothing.

## Access

Access is still read from `workspace_member`, in `app/crud/workspace.py`: the web
session check, every web route, every MCP route, personal access tokens and OAuth
connections. Nothing else decides who reaches a workspace.

`app/crud/agency.py` is the only code that writes those rows for a person in an agency,
which is how the two tables stay in step:

- "all workspaces": a row for every workspace of the agency, and a new row whenever a
  workspace is created there (`add_workspace`);
- chosen workspaces: exactly the chosen rows;
- a change or a removal rewrites only rows for that agency's workspaces, never
  another agency's.

A chosen workspace that is not the agency's is refused, so membership of one agency can
never give a workspace of another.

## Rules

- **Sign-up** (web, Google, the account form where an assistant connects) makes an
  agency named from the email's domain, with the person as its Admin, and their first
  workspace in it.
- **Only Admins create workspaces,** on the web and through `create_workspace`
  (Decided by Dmytro, 2026-11-23). A Member is refused with the Admins' names. On the
  web the workspace goes into the agency of the workspace the person has open; an
  assistant passes `agency_id` only when its person is an Admin of several agencies.
- **An agency always keeps at least one Admin:** removing the last one, or making them
  a Member, answers 409.
- **Removing a person** takes away the agency's workspaces at once, on the web and for
  their assistants. A web session issued for one of those workspaces is refused. If
  they reach another workspace, it is opened for them. With none left, sign-in answers
  403 "You no longer have access to any workspace"; the account itself stays.
- **What a removed person did stays on record.**

## Invites

An Admin invites people by email from Agency settings › Members, or their assistant
does after a yes. An invite (`agency_invite`) is for one address and carries the role,
the workspaces (all, or at least one chosen) and "can approve" the person will get.

- **The link** works once and for 7 days after it was last sent. Only its hash is
  stored. "Resend invite" makes a new link and restarts the 7 days; the old link stops
  working. "Cancel invite" ends it, and so does the invited person declining.
- **Who cannot be invited:** an address that is not an email, one already in the
  agency, and one that already has an open invite. Each comes back with its sentence.
- **Joining needs the invited email** (Proposed by Claude, accepted with the plan): a
  session signed in with it, a new account made for it on the invite page, or Google
  sign-in that returns it. A forwarded link is useless to another address.
- **A person who joins gets the inviting agency only,** never one of their own (Decided
  by Dmytro, 2026-11-23). An existing account keeps the agencies it had.
- **Email** is sent after the response, through the sending built for password reset.
  Without email settings, or when the provider refuses, the invite still exists and
  "Resend invite" tries again. The free plan in use sends 100 emails a day.
- An expired, cancelled, used or unknown link is the same 404.

## What "can approve" refuses

The design's sentence: "People who can approve may archive issues, close incidents,
override the gate, and change the Playbook and checks, in the workspaces they can
access." Of those, two exist today and are refused for a person without it, with the
names of the people who can approve in that workspace:

- archiving and unarchiving an issue, on the web and through `archive_issue` and
  `unarchive_issue` (which record the decision as approved by the assistant's person);
- changing a check's settings.

Resolving an issue and answering the assistant's clarification questions need no
approval (Decided by Dmytro, 2026-11-23). Closing incidents, overriding the gate and
changing the Playbook take the same rule (`require_approver`) when they are built.

## Routes

| Route | Who | What |
|---|---|---|
| `GET /api/v1/agencies/` | Anyone signed in | Their agencies, with their role in each |
| `GET /api/v1/agencies/{id}` | Anyone in it | The agency, its workspaces and its people |
| `PATCH /api/v1/agencies/{id}` | Admin | Rename |
| `PATCH /api/v1/agencies/{id}/members/{user_id}` | Admin | Role, workspaces, can approve |
| `DELETE /api/v1/agencies/{id}/members/{user_id}` | Admin | Remove the person |

| `POST /api/v1/agencies/{id}/invites` | Admin | Invite one or several emails |
| `POST /api/v1/agencies/{id}/invites/{invite_id}/resend` | Admin | New link, 7 more days |
| `DELETE /api/v1/agencies/{id}/invites/{invite_id}` | Admin | Cancel |
| `GET /api/v1/invites/{token}` | Anyone with the link | Which agency invites which email |
| `POST /api/v1/invites/{token}/accept`, `/decline` | Signed in with the invited email | Join, or end the invite |
| `POST /api/v1/invites/{token}/signup` | Anyone with the link | New account for the invited email, joined and signed in |
| `POST /api/v1/invites/{token}/signin` | Anyone with the link and the account's password | Signs in to the invited email's account and joins; also for a person with no workspace left, whom the ordinary sign-in refuses |

An agency a person is not in answers 404, the same as one that does not exist.

## Assistant tools

`list_people` for anyone's assistant; `invite_people`, `update_person` and
`remove_person` (which also cancels an invite) for an Admin's assistant, each only
after the person says yes. They call the same rules as the screen. Guide:
`connexity://guides/people`.

## The migration (0048)

Workspaces that shared a person became one agency, named from its oldest member's
email domain (an Admin can rename it). Everyone existing became an Admin who can
approve. A person who was in every workspace of their agency got "all workspaces";
anyone else kept exactly the workspaces they had. `workspace_member` was not changed,
so nobody's access changed that day, and the downgrade only removes the new tables.
