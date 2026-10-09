# A tool call opens to its n8n execution

- **Owner:** Dmytro
- **Slice:** 1.4

## Goal

Show what a skill actually did. A trace today says the agent called a tool and what came
back. It does not say what happened inside the backend that answered. After this merges,
a company can connect its n8n, link it to an agent, and each backend tool call on that
agent's calls opens to the n8n execution it triggered, node by node, with inputs,
outputs, status and timing.

## Changes

**n8n connection**

- n8n becomes a kind of integration, next to Retell, Vapi and ElevenLabs. It belongs to
  one company. Its API key is stored encrypted and shown masked, as for the others.
- An integration gains an address (`base_url`), because every n8n instance has its own.
  It is required for n8n and empty for the voice providers.
- A company can connect several n8n instances.
- Saving the connection tests it first with one read call to n8n. A wrong address or key
  is refused with a clear message.
- The address must be `https`, and addresses that point at private or local networks are
  refused. A new setting, off by default, allows them for a self-hosted Connexity and
  for local development.
- The existing Integrations form gains n8n as a choice, with an address field.

**Mapping a tool to its workflow**

- New: on an agent, each tool can be mapped to the n8n workflow that serves it: an n8n
  connection of the company, and one workflow in it. Connexity looks for a tool call's
  execution only among that workflow's executions.
- The tools listed are the tool names seen in the agent's calls. A tool that has never
  been called does not appear yet.
- A tool with no mapping has no backend (ending the call, for example). Nothing is
  looked up for it.
- Set through the API, and through a table on the agent's connection screen with two
  dropdowns per tool: the connection, then the workflow. The workflow dropdown is
  filled by reading the workflow names from that n8n.

**Executions**

- Two new tables, stored as rows:
  - an execution: the call and the tool call it belongs to, the n8n connection it came
    from, its id in n8n, the workflow's id, name and version, status, start, end, and
    how it was matched;
  - a step: one node run within an execution, in order, with the node's name and type,
    status, start, duration, input, output and error.
- The tables use the words "execution" and "step", not n8n's words, so another backend
  can fill them later.
- Executions are copied into Connexity. n8n deletes its history after a while, so a link
  to n8n would stop working.
- An execution is tied to its tool call by the call and the event's id within the trace,
  so that replacing a call's trace does not lose its executions.

**Finding and matching (open question Q4)**

- When a Retell call is stored, by pull or by webhook, then for each tool call whose
  tool is mapped, Connexity asks that n8n for the mapped workflow's executions that
  started during the call. n8n can filter by workflow and by start time, so this is a
  direct question, not a search through history.
- An execution belongs to a tool call when its trigger carries **this call's id, the
  same tool name and the same arguments**. If one call made the same tool call twice
  with the same arguments, the one closest in start time wins. This is an exact match,
  and it needs no change to the workflows.
- If the trigger carries no call id (the Retell tool is set to send arguments only),
  the match falls back to arguments and start time within the call, and is labelled a
  guess.
- New: an action to look again for one call's executions, for calls stored before the
  mapping existed.

**API and screen**

- The call's trace response gains its executions, each with its steps.
- In the call drawer, a tool call that has an execution expands to the list of nodes.
  Each node shows status and duration and opens to its input and output. A guessed match
  is marked as a guess.

**The rule about the UI (documents only)**

- The rule "no creation forms" is replaced in `CLAUDE.md`, `frontend/CLAUDE.md`, the
  vision, the lifecycle guide and `REBUILD.md`: the UI may do anything the assistant
  can do through the API. Chat, editors for the agent's prompts or workflows, deploying
  or writing to providers, and AI that generates content inside the product stay out.
  Slice 1.8 adds assistant tools for connections beside the forms; it removes none.

**Built in two steps, in one pull request**

1. The connection and the link. Dmytro then connects a real n8n to the local app.
2. Claude looks at the shape of real executions (field names and counts only), confirms
   or corrects the matching above with Dmytro, then builds executions, matching, the API
   and the screen.

## Decisions

Made by Dmytro on 2026-10-09:

- **n8n is connected per company, as an integration with an address.** Not through
  server settings: the product is multi-tenant.
- **A tool is mapped to its workflow**, per agent: one row per tool name, pointing at
  one workflow in one n8n connection. This replaces linking an agent to an n8n instance
  (decided the same day, then changed: searching a whole instance for a call's
  executions was the wrong design).
- **Tool names come from the agent's observed calls**, for now.
- **The connection is entered in the existing Integrations form**, which stays.
- **The UI is not held back.** Anything the assistant can create or change in Connexity
  through the API, a person can also do in the UI. Nothing removed in the rebuild comes
  back because of this, and AI that generates content (an internal assistant, test case
  generation) stays outside Connexity. AI inside the product for evaluations may come
  later; not decided.
- **The address must be `https`, and private addresses are refused** unless a setting
  allows them.
- **An n8n that hosted Connexity cannot reach is not supported yet.** Having the
  workflow push its execution to Connexity is a later slice.

Proposed by Claude, not yet confirmed:

- The matching rule above (call id, tool name and arguments; start time breaks a tie).
- The trigger's copy of the call is not stored. Retell sends the whole call, including
  the transcript so far, with every tool request, and the trace already holds it. The
  trigger step keeps the tool name and arguments only.
- Node inputs and outputs are stored as n8n returns them, with no redaction.
- Limits: an execution's stored data is capped (proposed 2 MB per execution and 200
  steps); beyond that the step is kept and its input and output are dropped, with a
  note saying so.
- Connexity only ever calls n8n's read endpoints for executions and workflows.

## Done when

- An n8n connection can be created, listed, tested and deleted through the API; the key
  is never returned; another company cannot see or use it.
- A wrong key, an unreachable address, an `http` address and a private address are each
  refused with a message that says which; with the setting on, a private address is
  accepted.
- A tool of an agent can be mapped to a workflow of an n8n connection of the same
  company, changed and cleared; not to another company's connection.
- The workflows of a connection can be listed for the dropdown; another company cannot.
- With invented n8n responses: an execution is matched by call id, tool name and
  arguments; two identical tool calls in one call each get their own execution; a
  trigger without a call id is matched as a guess; an execution from another call is
  not matched; a tool call with no execution has none; a
  failed node shows as failed with its error.
- n8n being slow, returning nothing, or returning something malformed does not stop the
  call from being stored. The call is stored without executions.
- Storing the same call again does not duplicate its executions, and replacing its trace
  keeps them.
- The trace response for a call includes its executions and steps; another company's
  call is not found.
- The drawer code compiles: a tool call with an execution expands to its nodes.
- **On real calls** (needs Dmytro's n8n connected locally): reported as counts, how many
  backend tool calls of the connected agent found an execution, by which method, and how
  many did not and why.
- `make check` passes.

## Out of scope

- A list of workflows, a browser of executions, or any execution not tied to a call.
- Running or testing a workflow.
- Workflow versions as components of a call (slice 1.5).
- Executions for Vapi and ElevenLabs calls (their calls are not traces yet, slice 1.3b).
- Sending executions through the ingest API.
- Push from an n8n that cannot be reached.
- Redacting personal data or secrets in node data.
- Tools for the assistant (slice 1.8).

## Risks

- **n8n keeps about 30 days of executions on the connected instance.** A call older
  than that can never be opened to its execution. Executions must be copied when the
  call arrives.
- **The time filter is not in n8n's documentation.** It works on the connected instance
  (see findings). An older n8n may ignore it; then every execution of the workflow
  would come back, and Connexity must stop at a limit instead of reading them all.
- **Node data can hold personal data and secrets** (customer details, tokens in
  headers). It is copied into Connexity's database as it is, apart from the trigger's
  copy of the call.
- **The key may be able to do more than read.** Read-only keys exist only on n8n's paid
  plans. Connexity only reads, but a leaked key would not be limited to that.
- **Fetching a user-supplied address** is a way to make the server call places it should
  not. The address rule above is the guard; a reviewer should check it is enough.
- **Setup is per tool.** Seven tools means seven rows to fill. Suggesting the mapping
  automatically is left for later.
- **A reviewer should push back if** storing node data without redaction is not
  acceptable even for now.

## Findings from the real n8n, before building step 2

Looked at the shape (field names, node types, counts; no content) of the n8n instance
Dmytro connected locally on 2026-10-09.

- 78 workflows, 48 with a webhook trigger. 14,756 executions, all from the last 30
  days. So history older than a month is gone.
- Listing executions accepts a start-time filter (`startedAfter`, `startedBefore`) and
  honours it, though the documentation does not list it.
- 973 executions were started by a webhook. 193 of them are Retell tool requests. Every
  one carries the tool name, the arguments, and the call with its id. 186 of them also
  carry the call's whole transcript so far.
- Each tool name is served by exactly one workflow.
- 26 of the 193 belong to calls that are in the local database. For all 26: call id,
  tool name and arguments identify exactly one tool call in the trace; the execution
  started less than a second from the tool call; and the workflow's response equals the
  result in the trace. 11 of the 26 are in calls that used the same tool more than
  once, and arguments told them apart every time.
- The other 167 belong to agents that are not connected to Connexity. The instance is
  shared, which is why the search must be narrowed to a workflow.
- 375 webhook executions had no readable trigger data. Not yet looked into.

## Outcome

### Deviations from the plan

- **The agent-level link was built, then replaced.** Step 1 first linked an agent to an
  n8n instance. Dmytro replaced that with tool-to-workflow mapping the same day. The
  link table, its routes and its screen section were removed before any commit.
- **A step stores its output and the names of the steps that fed it, not a separate
  input.** n8n keeps only each node's output; a node's input is the output of the nodes
  before it. Storing both would double the data. The screen says "Input: the output of
  X".
- **During a pull, only a call seen for the first time is looked up.** A call already
  stored is looked up on request ("Find executions"), not on every pull.
- **After a webhook, the lookup runs once the response has been sent**, because Retell
  waits only ten seconds for an answer.
- **A later look that finds nothing leaves stored executions in place.** n8n forgets;
  Connexity keeps what it copied.
- **Requests go to the address that was checked.** The plan said the address is checked.
  Review found that checking and then connecting by name lets a host answer differently
  the second time. Connexity now connects to the checked IP address and presents the
  real host name for TLS.
- **The trigger's data is removed wherever it reappears**, not only on the trigger step.
  Nodes that pass their input on would otherwise have kept the request headers and the
  copy of the call.
- **If an n8n refuses the time filter, executions are read without it**, newest first,
  up to a limit of 500 per workflow per call.
- **An error's stack trace is not stored.** Not in the plan.
- **The Integrations form now shows the server's own error message.** It used to show a
  fixed "check your API key" for every failure.
- **A public page was added**, `docs/traces/n8n.md`.
- Limits as proposed: 2 MB of node output and 200 steps per execution.

### Check results

`make check` on this branch:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 8s |
| Backend tests and coverage | ok | 58s |
| MCP server tests | ok | 2s |
| Frontend lint | ok | 8s |
| Frontend types | ok | 6s |
| Generated client is fresh | ok | 10s |

The plan step failed in the full run because this Outcome was not yet written. It was
re-run on its own afterwards and passed; nothing else changed in between.

Against the done-when:

| Done when | Result |
|---|---|
| n8n connection created, listed, tested, deleted; key never returned; other company shut out | Yes |
| Wrong key, unreachable address, `http` and private address each refused with its own message; the setting allows private | Yes. Twelve kinds of private or local address are tested, including a private IPv4 address written as IPv6 |
| A tool mapped, changed and cleared; not to another company's connection | Yes. Also refused: a workflow that does not exist, a voice account, a workflow id that is not a plain id |
| Workflows listed for the dropdown; another company cannot | Yes |
| Matched by call id, tool name and arguments; two identical tool calls each get their own; no call id gives a guess; another call's execution is not matched; no execution means none; a failed node shows its error | Yes, one test each |
| A slow, empty or malformed n8n does not stop the call being stored | Yes: at the client (timeout, empty, not JSON, wrong shape), and end to end through a pull with n8n failing |
| Storing again does not duplicate; replacing the trace keeps executions | Yes |
| Trace response includes executions and steps; another company's call is not found | Yes |
| The drawer compiles with a tool call expanding to its steps | Compiles and lints. **Not looked at in a browser by Claude** |
| Real calls | See below |
| `make check` passes | Yes, with the note above |

Real calls, on Dmytro's machine, counts only. Dmytro connected an n8n and mapped two
tools of one agent. The built lookup was run on that agent's 50 calls from the last 31
days:

| Measure | Result |
|---|---|
| Tool calls on those calls | 97 |
| Tool calls whose tool is mapped | 29 |
| Found an execution | 27, all exact matches |
| The workflow's response equals the tool result in the trace | 27 of 27 |
| Not found | 2, both on a call 30 days old; n8n no longer has any execution of those workflows from that time |
| Steps stored | 209 (about 8 per execution), none over the size limit |
| Stored output containing a request signature or a transcript | 0 |
| n8n problems | 0 |
| Time for all 50 calls | 9 seconds |

The run was repeated after the review fixes with the same numbers, so connecting to the
checked address works against a real n8n.

Migration `0005_n8n_executions` applies, reverses and re-applies on the local test
database, and `alembic check` reports no drift.

**`/code-review`** was run on the whole diff before the fixes below. Ten findings; nine
fixed, one left:

| Finding | Outcome |
|---|---|
| The address was checked, then resolved again for the request | Fixed: requests go to the checked address |
| Trigger headers and the copy of the call survived in nodes that pass input through | Fixed: removed wherever they reappear |
| No fallback if an n8n refuses the time filter | Fixed |
| A workflow id was put into the request path unescaped | Fixed: plain ids only, and escaped |
| Arguments that are not an object could never match | Fixed: kept the same way the trace keeps them |
| The "N of M" line could show for a different call | Fixed |
| A missing workflow was detected by matching an error's text | Fixed |
| An empty address was refused for a voice provider | Fixed |
| A database session opened by hand in a routes file | Fixed: moved to the service |
| During a pull, executions are looked up one call at a time inside the request | **Not fixed.** See below |

The review was done by the session that wrote the code, not an independent reviewer.

### Not done

- **Not seen in a browser by Claude.** Dmytro connected n8n and mapped two tools in the
  local app; the execution view in the drawer is type-checked only.
- **Slow first pull.** A pull that brings in many new calls for an agent with mapped
  tools asks n8n once per call per workflow, one after another, inside the request.
  Fifty calls took nine seconds; hundreds would take minutes. Reading a workflow's
  executions once for the whole batch would fix it.
- **The guess path and failed nodes are tested on invented payloads only.** Every real
  execution carried the call id, and none had a failed node.
- **375 webhook executions on the real instance had no readable trigger.** Not looked
  into. They did not belong to the mapped workflows.
- **Only two of the agent's tools were mapped** for the real check.
- **Node data is stored without redaction**, as decided for now.
- **An n8n that hosted Connexity cannot reach** is not supported.
- **Tools appear for mapping only after a call has used them.**
- **The webhook's own lookup was not exercised against Retell**; only through tests.
- **The local n8n connection lost its address once** during the rework (a local
  migration was rolled back and forward). Dmytro re-entered it. Nothing shipped is
  affected; the migration in this pull request is a single forward step.
