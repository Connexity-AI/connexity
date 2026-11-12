# Connect an assistant to Connexity

Each person connects their own assistants. An assistant reaches the workspaces that
person can reach and acts on their behalf; everything it does is recorded as done by
their assistant. Use the MCP address of your Connexity, for example
`https://mcp.connexity.ai/mcp`.

## Claude Code

1. Run `claude mcp add --transport http connexity <MCP address>`.
2. In Claude Code, run `/mcp`, choose `connexity` and authenticate. A browser opens.
3. Sign in to Connexity (or create an account) and press **Allow**.

## ChatGPT

Custom connectors need ChatGPT's developer mode, which depends on your ChatGPT plan.

1. In ChatGPT, open Settings, then Apps & Connectors, then Advanced settings, and turn on
   developer mode.
2. Create a connector: give it a name, paste the MCP address, and choose OAuth.
3. Sign in to Connexity (or create an account) and press **Allow**.
4. In a chat, turn on the connector and ask it to list your Connexity workspaces.

## After connecting

Call `list_workspaces`, then `get_readiness` for the workspace you work in. Readiness's
first step, "Assistant connected", shows your assistant's name.

## Voice platforms

Once you are connected, connect the workspace's voice platform with
`connect_voice_platform`:

1. Ask the person for the API key. In Retell it is in the dashboard, under API Keys.
   Suggest they create a key just for Connexity.
2. Call `connect_voice_platform` with the `workspace_id`, `platform` ("retell") and the
   key. Do not repeat the key in your reply.
3. Connexity checks the key with the platform and stores it encrypted. It only reads
   from the platform; it never changes agents there.

Connecting again replaces the key. Vapi and ElevenLabs connect the same way.

## Choosing agents

Once Retell is connected, add the agents this workspace should watch with `add_agents`.
Connexity does not list Retell's agents for you; use your own access to Retell.

1. Look at the Retell account's agents and their recent calls.
2. One Retell account often holds several clients' agents. Recommend the ones that
   belong to this client and take real calls; leave out tests, drafts and agents with no
   recent calls.
3. Ask the person to confirm the list.
4. Call `add_agents` with their Retell agent ids. Each needs to be in the Retell account
   connected to this workspace.
5. Call `list_agents` to check, and `get_readiness`.

Only added agents are synced. An agent cannot be removed from a workspace yet, so ask
before adding.
