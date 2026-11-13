# Readiness

Readiness is how complete a workspace's setup is, aimed at 100%. You do the setup; the
person gives keys and approves. It never changes the agents' score.

Call `get_readiness` with a `workspace_id` to see the steps, which are done, and what to do
next. Call it again after each step and tell the person what changed.

## Getting started

1. **Assistant connected:** done once you are connected, as now.
2. **Voice platform connected:** the workspace has a voice platform connection (Retell
   first). Ask the person for their API key and call `connect_voice_platform`. Never
   repeat the key.
3. **Agents and calls synced:** the agents the person chose are added with `add_agents`
   and their webhook is set in Retell. In progress while their past calls come in
   ("640 of 1,284 calls · 2 of 5 agents"); done when every added agent's first scan has
   finished.
4. **First scan done:** done the first time step 3 is done, with how many calls and
   agents are in Connexity and how many calls have no resolved version. It stays done
   when agents are added later; their own scans still run.

## The first scan

Call `scan_calls` with the `workspace_id` once agents are added, and keep calling it
until it says finished. Each call does up to about a minute of work and says how far
it has got; tell the person now and then.

- It brings in each added agent's calls from the last 30 days, reads each in full,
  turns it into a trace and resolves the agent version that served it.
- Calls after the scan starts arrive by webhook, so set the webhook first.
- Calls already stored, by the webhook or an earlier step, are skipped. If Retell
  cannot be reached, call it again: it carries on where it stopped.
- An agent added later is scanned the next time you call `scan_calls`.
- A call whose version Retell no longer has is stored without one and counted; nothing
  needs doing.

Until the first scan is done, the web app shows Readiness instead of everything else.

## Later

The controls come in later milestones: alerts to Slack, an incident channel you watch,
a spec for each agent, backends connected, tests covering 80% of each spec, the
deployment gate, and automatic rollback.
