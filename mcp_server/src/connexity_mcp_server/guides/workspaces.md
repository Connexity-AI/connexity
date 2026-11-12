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
- For a new client, ask the person for the client's name, then call `create_workspace`.
  Only the person is a member; there are no invitations yet. Creating one does not
  change the workspace the person has open in the web app.
