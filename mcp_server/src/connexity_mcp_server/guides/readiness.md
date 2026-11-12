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
   and their webhook is set in Retell (in progress, counting calls as they arrive), and
   their past calls are in Connexity (done, with the first scan).
4. **First scan done:** every synced call is turned into a trace with its versions.

Until the first scan is done, the web app shows Readiness instead of everything else.

## Later

The controls come in later milestones: alerts to Slack, an incident channel you watch,
a spec for each agent, backends connected, tests covering 80% of each spec, the
deployment gate, and automatic rollback.
