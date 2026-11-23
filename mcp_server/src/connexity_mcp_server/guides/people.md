# People in the agency

An agency is the account above the client workspaces. It owns the people. Clients
never log in.

## What each person has

- **Role.** An `admin` manages people and billing and creates workspaces. A `member`
  works in their workspaces.
- **Workspaces.** All of the agency's workspaces, including ones created later, or
  only chosen ones.
- **Can approve.** Whether they may make the critical decisions in their workspaces:
  archiving or unarchiving an issue and changing a check today; closing incidents,
  overriding the gate and changing the Playbook when those exist.

A person's assistants reach exactly what the person reaches, and lose a workspace the
moment the person does. You are one of those assistants.

## Reading

`list_people` answers who is in the agency of a workspace: each person, the invites
still waiting (for an admin's assistant), and the agency's workspaces so you can name
them. Use it to answer "who has access to this client?".

## Changing people

Only when the person you act for is an `admin`, and only after they said yes to the
exact change. Say what will happen first, then wait for the yes.

- **Invite:** `invite_people` with the addresses, the role, the workspaces and whether
  they can approve. Ask for anything the person did not say; do not assume "can
  approve". Each address gets an email with a link that works once and for 7 days. An
  address that is already in the agency, or already invited, gets nothing and comes
  back with the reason.
- **Change:** `update_person`. Naming `workspace_ids` means "only these".
- **Remove:** `remove_person` with a person's `id`. Tell the person first how many
  workspaces and connected assistants (`assistants`) the removed person loses. What
  they did stays on record. With an invite's `id` the same tool cancels the invite.

An agency always keeps at least one admin: the last one cannot be removed or made a
member. Make someone else an admin first.

## When a decision is refused

`archive_issue` and `unarchive_issue` record a decision as approved by the person you
act for. If that person cannot approve, the tool is refused and names who can. Tell
the person, and leave the issue as it is.
