# Connect your assistant

Connexity is worked through an AI assistant: it reads calls, issues and specs and does
the operational work through Connexity's MCP tools. Each person connects their own
assistants. An assistant reaches the workspaces that person can reach and acts on their
behalf, and everything it does is recorded as done by their assistant.

You need the MCP address of your Connexity. For the hosted product it is
`https://mcp.connexity.ai/mcp`; when you run Connexity yourself it is your MCP server's
address, `http://localhost:8001/mcp` by default.

Every tool the assistant gets, and whether it needs your yes, is listed on the MCP page
of your Connexity at `/mcp-docs`
([app.connexity.ai/mcp-docs](https://app.connexity.ai/mcp-docs) for the hosted product).

## Claude Code

Claude Code connects with a personal access token, without a browser sign-in. It works
the same in the Claude Code app and in a terminal.

1. In Connexity, open the Work page. Until an assistant is connected, its first task is
   "Connect your AI assistant": press **Show how**, then **Copy setup prompt**.
2. Paste the prompt into Claude Code and let it run the `claude mcp add` command it
   contains.
3. Start a new Claude Code session. Connexity's tools load in it.

The token acts as you in every workspace you can reach, and works until you revoke it
in Account, under Assistant access. Each copy creates a new token; earlier ones keep
working until revoked.

If a token cannot be used, sign in from a terminal instead: run
`claude mcp add --transport http --scope user connexity <MCP address>`, then `/mcp`,
choose `connexity` and authenticate in the browser that opens.

## Claude

In Settings, then Connectors, add a custom connector with the MCP address, click
Connect, sign in to Connexity (or create an account) and press **Allow**.

## ChatGPT

Custom connectors need ChatGPT's developer mode, which depends on your ChatGPT plan.

1. In ChatGPT, open Settings, then Apps & Connectors, then Advanced settings, and turn
   on developer mode.
2. Create a connector: give it a name, paste the MCP address, and choose OAuth.
3. Sign in to Connexity (or create an account) and press **Allow**.
4. In a chat, turn on the connector and ask it to list your Connexity workspaces.

## After connecting

Ask the assistant to set Connexity up. It connects your voice platform (Retell today),
adds the agents you choose, brings in their calls from the last 30 days and writes each
agent's spec. From then on it asks Connexity for its next task.

Nothing the assistant does changes an agent through Connexity: Connexity never edits,
deploys or calls an agent. The assistant makes changes with its own access to your
voice platform.
