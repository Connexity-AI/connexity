# n8n executions

When an agent's tools are served by n8n workflows, Connexity can show what a workflow
did for each tool call: every node that ran, in order, with its output, status and
duration. The execution is attached to the tool call in the call's trace. There is no
list of workflows and no browser of executions; an execution exists in Connexity only
as something a call's tool call triggered.

## 1. Connect n8n

Add an n8n connection on the Integrations page, or with the API:

```bash
curl -X POST "$CONNEXITY_URL/api/v1/integrations/" \
  -H "Content-Type: application/json" --cookie "auth_cookie=$YOUR_SESSION" \
  -d '{"provider": "n8n", "name": "Production n8n",
       "base_url": "https://your-name.app.n8n.cloud", "api_key": "..."}'
```

- The connection belongs to your company. A company can connect several instances.
- The key is stored encrypted and never returned.
- Connexity only reads: the list of workflows, and executions. If your n8n plan has
  scoped API keys, use one limited to reading workflows and executions.
- The address must be `https` and reachable from Connexity. An address that points to a
  private or local network is refused. A self-hosted Connexity can allow those with
  `ALLOW_PRIVATE_INTEGRATION_URLS=true`.
- An n8n that Connexity cannot reach (behind a firewall) is not supported yet.

## 2. Map each tool to its workflow

On the agent's Environments tab, under **Tool backends**, each tool seen in the agent's
calls can be mapped to the workflow that serves it. With the API:

- `GET /api/v1/agents/{agent_id}/tools` lists the tools and their mappings.
- `GET /api/v1/integrations/{integration_id}/workflows` lists a connection's workflows.
- `PUT /api/v1/agents/{agent_id}/tool-backends` with
  `{"tool_name", "integration_id", "workflow_id"}` sets a mapping.
- `DELETE /api/v1/agents/{agent_id}/tool-backends?tool_name=...` removes it.

A tool with no mapping has no backend. Leave tools built into the voice provider (ending
the call, for example) unmapped. Nothing is looked up for them.

A tool appears in the list once a stored call has used it.

## 3. What happens then

When a call arrives, by pull or by webhook, then for each tool call whose tool is mapped
Connexity asks that n8n for the mapped workflow's executions that started during the
call, and copies the one that belongs to the tool call.

**An execution belongs to a tool call when its trigger received this call's id, the same
tool name and the same arguments.** Retell sends all three with a tool request. If one
call used the same tool twice with the same arguments, the execution closest in start
time is taken. This is shown as an exact match.

If the trigger received no call id (the Retell tool is set to send arguments only), the
execution is matched on arguments and a start time within ten seconds of the tool call.
This is shown as a **guess**.

- For a call stored before its tools were mapped, use **Find executions** on the call,
  or `POST /api/v1/calls/{call_id}/executions/refresh`.
- **n8n deletes old executions** (after 14 days by default; it is a setting of the
  instance). A call older than that can no longer be opened to an execution. Executions
  already copied into Connexity stay.
- If the instance is set not to save successful executions, only failed ones can be
  shown.
- If n8n cannot be read, the call is stored without executions.

## What is stored

`GET /api/v1/calls/{call_id}/trace` returns `executions` beside the trace:

| Field | Meaning |
|---|---|
| `event_id` | The id of the tool call in the trace that this execution belongs to. |
| `provider`, `external_id` | `n8n`, and the execution's id in n8n. |
| `workflow_id`, `workflow_name`, `workflow_version` | The workflow, and the version of it that ran. |
| `status` | `ok`, `error`, `running`, `canceled` or `unknown`. |
| `started_at`, `ended_at` | When it ran. |
| `match` | `exact` or `guess`. |
| `steps` | The node runs, in the order they ran. |

A step has `name`, `kind` (the node type), `status`, `started_at`, `duration_ms`,
`output`, `error`, and `input_from`: the names of the steps whose output was its input.
n8n keeps each node's output only, so a step's input is not stored a second time.

Three things are deliberately not stored:

- **The trigger's request headers.** They carry the provider's signature.
- **The trigger's copy of the call.** Retell sends the whole call, with the transcript so
  far, with every tool request. The trace already has it. The trigger step keeps the tool
  name and arguments.
- **An error's stack trace.**

Everything else a node produced is stored as n8n returned it, including any customer
data in it. There is no redaction. An execution keeps at most 2 MB of node output and
200 steps; past that a step is kept without its output and marked.
