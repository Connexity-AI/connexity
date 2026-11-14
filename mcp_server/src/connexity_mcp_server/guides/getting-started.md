# Getting started with Connexity

Connexity records every call your team's conversational AI agents take, checks it, and
shows people a quick glance at the fleet. You, the assistant, do the operational work
through these tools: you watch, investigate and fix. People approve where a decision is
theirs.

## How the tools work

1. **Start with `list_workspaces`.** A workspace is one client's agents, calls and
   settings. Every other tool takes a `workspace_id`.
2. **Every answer has the same shape:**
   - `data`: the facts.
   - `rules`: the rules that apply to them. Follow them.
   - `next_steps`: what you can do next, in order, naming the tool.
   - `guide`: the guide for this part of Connexity.
   - `next_cursor`: on lists, pass it back as `cursor` for the next page. It is empty
     on the last page.
3. **Errors** have the same shape: an `error` message and `next_steps` to recover.

## One agent at a glance

`get_agent` answers what the agent page shows: its platform, type, live version and
model, the workflows it used, its calls and its latency per day with version marks.
Latency is a basic measure from the calls' turns; the answer's rules say how it is
worked out.

## After setup: the spec

Once the first scan is done, write each agent's spec: what it is supposed to do, as
plain rules from its prompt. Read `connexity://guides/spec`, call `get_spec` with
`include_prompt` for the prompt Connexity recorded, then `write_spec`. When an agent
moves to a new version, Connexity copies its spec and `get_spec` says it needs review.

## What Connexity never does

Connexity never edits, deploys or calls an agent, and never writes to a voice platform,
workflow tool or CRM. It records and verifies. Changes to an agent are yours to make in
the team's own tools, with a person's approval.
