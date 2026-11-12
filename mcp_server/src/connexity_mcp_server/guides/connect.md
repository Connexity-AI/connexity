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
