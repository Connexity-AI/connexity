# Who does what: Connexity, the assistant and the person

How work is split between Connexity, the user's AI assistant (Claude Code, ChatGPT or
similar, through MCP) and the person. Each statement is marked Decided, Proposed or
Open. The full job-by-job table is [`designs/who-does-what.md`](../designs/who-does-what.md).

## The default rule (Decided 2026-11-12)

Whatever the assistant can do is the assistant's job, guided by Connexity's best
practices. That is the fastest way to production. Connexity takes a job over later,
when owning it as a platform clearly makes sense.

| Party | Does |
|---|---|
| **The assistant** | The work: connects platforms and backends, writes the spec, writes test cases, writes fixes, writes the roadmap, deploys. |
| **Connexity** | Watches and verifies: records every call, runs checks, groups issues and incidents, detects behaviour the spec does not cover, runs tests and the gate, sends alerts, keeps every decision record. It never changes or deploys an agent. |
| **The person** | Approves and owns the business: confirms decisions that change numbers or remove protection, answers questions only they can answer, owns the client. Anything a person does can also go through their assistant, unless a rule says a person must confirm. |

## Exceptions to the default rule (Decided 2026-11-12)

- **Verification stays with Connexity:** checks, test runs and the gate. The assistant
  must not grade its own work.
- **Watching calls stays with Connexity,** including spec drift (behaviour the spec does
  not cover, or goes against): it is observability, and the assistant does not run all
  the time. "Spec drift" is an internal term, not shown in the UI.
- **Grouping failures into incidents is Connexity's;** the assistant or a person corrects
  it.

## What a person must confirm (Decided)

- Archiving an issue (it stops counting).
- Closing an incident.
- Shipping a version that failed its tests, like a force push, with a reason.
- Changing a check's setting (off, flags, fails the call).
- Clarification answers the assistant prepared: it confirms them with the person in a
  batch ("I can answer 75 confidently; I need your help with the other 7").

The assistant may propose each of these; the proposal appears for a person to confirm.
Every one is a decision record.

## Acting without a person in the moment (Decided 2026-11-12)

An allow list, not a block list. Connexity predefines the actions that may ever run
without a person; a team can only switch those on, per agent, each with an "approve
automatically" choice. It starts with incidents only (roll back to the last version that
passed its tests; a hotfix that passes its tests), set on the Incidents page's Playbook
and built after the gate. The flow: Connexity opens an incident and alerts Slack; the
assistant, if connected to that channel, checks the rules in Connexity through MCP and
follows them, asking the person in its session unless the rule is approved
automatically. Every action taken this way is recorded with the rule that allowed it.

## How the assistant is kept on Connexity's practices (Proposed)

From weakest to strongest: instructions sent when it connects; tools shaped around the
work; every answer carrying the next step and the guidance for it ("push, don't pull");
short guides served through MCP; a Claude Code plugin with skills and the pre-deploy
hook; and Connexity's own verification and records, which catch what slips through.
