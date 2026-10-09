# Which version served a call

Every call lists what served it, each with a version and a fingerprint of its content:

| Kind | What it is | Where it comes from |
|---|---|---|
| `agent` | The voice agent's settings: voice, language, timeouts and the like. | Retell, at the agent version the call carries. |
| `prompt` or `flow` | The prompt text, the opening message and the tool definitions; or a conversation flow's nodes. | Retell, at the prompt version that agent version points to. |
| `model` | The model and its settings. | The same read. |
| `skill` | A backend workflow that ran on the call. | The n8n execution, which carries the workflow as it ran. See [n8n executions](./n8n.md). |

Connexity keeps each version it has seen once, with its content, in a catalogue per
agent.

## Fingerprints

A fingerprint is a hash of a version's content. Fields that change without the content
changing are left out: timestamps, the version number itself, publish flags, version
titles, and where a workflow's nodes sit on the canvas. So:

- two versions with the same content have the same fingerprint, even under different
  version numbers;
- a different fingerprint means the content differs.

A call also has one **state fingerprint**, over its agent, prompt (or flow) and model.
Calls with the same state fingerprint were served by the same voice-side configuration.
Skills are not part of it, because a call only knows the versions of the workflows it
actually used.

## When versions are read

- The first call on an agent version Connexity has not seen makes it read that version
  from Retell, once. Later calls on the same version read nothing.
- A workflow version is recorded when an execution of it is copied. n8n can only return
  a workflow's current version, so a version no call has used is never seen.
- If Retell cannot be read, the call is stored with its agent version number only.
- Calls stored earlier, or while Retell could not be read, are worked out in the
  background the next time the agent's calls are synced. Nobody has to ask. If a pass
  cannot finish (Retell is down, or no longer has a version), the next one waits ten
  minutes.
- `POST /api/v1/agents/{agent_id}/versions/resolve` does the same on request and
  reports what it did. It reads each agent version once and can be run again.

## Reading it

- A call (`GET /api/v1/calls/{call_id}`) has `agent_version` and `state_fingerprint`.
- A call's trace (`GET /api/v1/calls/{call_id}/trace`) has `served_by`: the list above,
  each entry with `kind`, `name`, `ref`, `version`, `fingerprint`, and
  `component_version_id` when Connexity holds the content.
- `GET /api/v1/agents/{agent_id}/component-versions` lists every version seen for an
  agent, without content. `?kind=prompt` narrows it.
- `GET /api/v1/agents/{agent_id}/component-versions/{id}` returns one with its content.

## What is stored, and what is masked

The content is stored as the provider returned it: the full prompt, the tool
definitions with their addresses, the workflow's nodes and their code. Two things are
replaced by `•••` before storing and before fingerprinting:

- every value under a field whose name contains "header" (request headers on tool
  definitions and on workflow nodes);
- the value of any field named like a key, token, secret or password.

Masking goes by the field's name. **A credential written into a prompt, or hard-coded
inside a workflow's code, is stored as it is.**

## For traces sent through the ingest API

A sender supplies `components` itself (see [the trace format](./trace-schema.md)). The
state fingerprint is computed from whatever `agent`, `prompt`, `flow` and `model`
components carry a `fingerprint`. Connexity does not read versions from a provider for
these calls.
