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

## Routes

| Route | Who | What |
|---|---|---|
| `GET /api/v1/agencies/` | Anyone signed in | Their agencies, with their role in each |
| `GET /api/v1/agencies/{id}` | Anyone in it | The agency, its workspaces and its people |
| `PATCH /api/v1/agencies/{id}` | Admin | Rename |
| `PATCH /api/v1/agencies/{id}/members/{user_id}` | Admin | Role, workspaces, can approve |
| `DELETE /api/v1/agencies/{id}/members/{user_id}` | Admin | Remove the person |

An agency a person is not in answers 404, the same as one that does not exist.

## The migration (0048)

Workspaces that shared a person became one agency, named from its oldest member's
email domain (an Admin can rename it). Everyone existing became an Admin who can
approve. A person who was in every workspace of their agency got "all workspaces";
anyone else kept exactly the workspaces they had. `workspace_member` was not changed,
so nobody's access changed that day, and the downgrade only removes the new tables.
