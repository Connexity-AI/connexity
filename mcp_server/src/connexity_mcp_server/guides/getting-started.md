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

## What to do next

Call `get_next_task` at the start of a session and after each task. Connexity sorts the
workspace's work and hands you the single most important task, with its facts, the
rules and numbered steps. Take tasks in that order; do not pick your own.

- **The order:** incidents, then Critical tasks, then setup (onboarding steps, then
  specs), then everything else, most calls first. A task that blocks a higher one sits
  above it.
- **Blocks and Blocked by.** Connexity works out which work waits for other work: an
  agent's open questions block its issue fixes, its spec to write or update blocks its
  fixes and calls to review, each onboarding step blocks the next, and the first scan
  blocks the specs. A blocked task is never handed to you; each task lists what it
  blocks and what blocks it.
- **Asking again ends your current task.** It is done when its work is gone. It waits
  for the person when the rest is theirs, such as resolving an issue once the fix is
  live. Otherwise it goes back to its place in the list.
- **Some tasks are the person's:** answering questions, connecting their assistant.
  The answer lists them under `waiting_for_person`; ask the person in your chat, and
  never decide for them.
- **Name your session.** Pass `session`, a few words for the work it is on such as
  `Onboarding`, and keep the same name for the whole session. Each session holds its
  own task, so several sessions of one assistant can work side by side; the answer's
  `in_progress` says what the others are on.
- **The person can reorder To do.** Their order wins for the tasks they moved, and the
  tasks you get follow it. When the person asks you to change the order ("do Night line
  first"), call `move_task`; never reorder on your own.
- **To see the whole list** without taking a task, call `list_tasks`: the Work page's
  list, with who is on what and what was done this week.
- **One workspace at a time.** Another session's task in progress is never handed to
  you.

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

Behaviour the prompt does not settle is a question for the person, never a rule you
write: raise it with `raise_clarifications`, ask the person in your chat, and submit
what they pick with `answer_clarifications`. Each answer becomes a spec rule.

During onboarding this is the last step: once the specs are written, raise what they
leave open, propose answers where you can, and ask the person once. They confirm your
proposals as a batch and answer the rest. When no question is left open, onboarding is
complete: tell the person their dashboard is ready, with the link Connexity gives.

## What Connexity never does

Connexity never edits, deploys or calls an agent, and never writes to a voice platform,
workflow tool or CRM. It records and verifies. Changes to an agent are yours to make in
the team's own tools, with a person's approval.
