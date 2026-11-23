# Workspaces

A workspace holds one client's agents, calls, issues and settings. An agency has one
workspace per client; nothing is shared between workspaces.

- You reach the workspaces that the person who connected you can reach, and you act on
  their behalf. Everything you do is recorded as done by their assistant.
- Call `list_workspaces` to see them. Pass a workspace's `id` as `workspace_id` to every
  other tool.
- A workspace you cannot reach answers "Workspace not found", the same as one that does
  not exist.
- When the person works with several clients, ask which client they mean before acting,
  and name the workspace in your answer.
- Every workspace belongs to an **agency**: the account above the workspaces, which
  owns the people and the billing. `list_workspaces` names each workspace's `agency`,
  the person's `role` in it and whether they `can_approve`. A person can be in more
  than one agency; workspaces of different agencies have nothing to do with each other.
- A person reaches all of an agency's workspaces, or only the ones chosen for them. You
  reach exactly what they reach, and lose a workspace the moment they do.
- For a new client, ask the person for the client's name, then call `create_workspace`.
  Only an `admin` of the agency can create one: for a `member` the answer names the
  Admins to ask, so tell the person that. Pass `agency_id` only when the person is an
  Admin of more than one agency, after asking which one the client belongs to.
  Everyone who reaches all of the agency's workspaces reaches the new one. Creating one
  does not change the workspace the person has open in the web app.
