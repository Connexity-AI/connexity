# Who does what: Connexity, the assistant, the person

A living document. One row per job in the agent's lifecycle. Update a row when a decision changes it; never leave two rows saying different things.

**The three parties**

- **Connexity** records, measures, checks, tells and gates. It never changes an agent, never deploys, never writes the agent's content, and never acts like an agent. It may use AI for metrics, evals and insights.
- **The assistant** (Claude Code or similar, through MCP) does the work: connects, investigates, writes, fixes, tests, deploys.
- **The person** approves, settles business questions, owns the client. Everything the person does can also be done through the assistant, unless the row says a person must confirm.

**Default rule (Decided 2026-11-12):** if the assistant can do a job, it is the assistant's job, guided by Connexity's best practices. That is the fastest path to production. Connexity takes a job over later, when owning it as a platform clearly makes sense. Exception (Decided 2026-11-12): verification stays with Connexity (records, checks, test runs, the gate), because the assistant must not grade its own work. Watching calls stays with Connexity too, because the assistant does not run all the time.

**Status:** Decided (Dmytro's words), Proposed, Open.

## Getting started

| Job | Connexity | Assistant | Person | Status |
|---|---|---|---|---|
| Sign up | Hosts the account | Guides the person to it | Signs up | Decided |
| Connect the assistant | Serves MCP and its docs; scopes every call to a workspace the person can access | Connects itself through MCP, per person (as many as they like) | Approves the connection | Decided 2026-11-12: connections are per user, reaching that user's workspaces |
| Connect the voice platform (Retell) | Syncs agents, versions and past calls | Registers the connection through MCP; no forms in the app | Gives the key, chooses which agents | Decided |
| Connect backends (n8n, CRM) | Reads executions and records, joins them to calls | Registers the connections | Gives access | Proposed |
| Infer each agent's spec | Stores it, versioned per agent version; serves the best practices for writing it; counts it in Readiness | Writes it from the prompt, guided by Connexity's best practices | Approves | Decided: a Readiness step on the roadmap, not automatic on connection |
| Drive Readiness to 100% | Measures it, shows what is missing | Works through the controls | Approves steps | Decided |

## Watching real calls

| Job | Connexity | Assistant | Person | Status |
|---|---|---|---|---|
| Record every call as one trace with versions | Does it | Reads it through MCP | Browses calls in the app | Decided |
| Run checks, raise findings, group into issues | Does it | — | — | Decided |
| Define classifier and judge checks | Runs them | Writes them as data | Can write them too | Decided |
| A check the assistant runs itself and reports | — | Not allowed, or advisory only (grading its own work) | — | Decided |
| Set each check to off, flags or fails | Records the decision | Proposes | Decides | Decided |
| Tip on every issue | Writes it | Uses it to fix | Reads it | Decided |
| Archive an issue | Records who, when, why; stops counting it | Proposes | Confirms | Decided |
| Compute the score | Computes it | — | — | Decided that only fixes move it; how it is made is Open |

## Spec and clarifications

| Job | Connexity | Assistant | Person | Status |
|---|---|---|---|---|
| Keep every agent's spec up to date (**spec drift**, an internal term, never shown in the UI): behaviour the spec does not cover, and behaviour against the spec | Detects both on real calls: not covered becomes a clarification, against the spec becomes a "Spec rule broken" issue | — | — | Decided: Connexity's job, it is observability and the assistant does not run all the time |
| Answer a clarification | Records the answer and who gave it; the answer becomes spec | Prepares answers and confirms them with the person in batches, then submits through MCP | Confirms the batch, or answers in the app | Decided |
| Spot a new prompt contradicting an earlier answer | Marks the rule in conflict, asks again | — | — | Decided |
| Park a clarification | Records it | Can park | Can park | Decided |

## Testing and the gate

| Job | Connexity | Assistant | Person | Status |
|---|---|---|---|---|
| Write test cases for spec rules | Stores them, links each to its rule, shows coverage | Writes them | — | Decided |
| Run tests (text, audio, phone) | Runs them on the agent's own engine | Starts them through MCP | Starts them in the app | Proposed |
| Run backend edge-case tests | Runs them (independent verification) | Writes them | — | Decided: verification stays with Connexity (answers P3) |
| Verify a candidate version | Returns Verified or Failed for its fingerprint | Asks before every deploy | — | Decided |
| Install the pre-deploy hook | Serves the hook and instructions | Installs it in its workspace | Approves | Proposed |
| Deploy | Never | Deploys | Approves the plan | Decided |
| Ship a version that failed its tests | Records the override | Carries it out | Must decide | Decided |
| Flag a version live without passing | Flags it, alerts | — | — | Proposed |

## Incidents and alerts

| Job | Connexity | Assistant | Person | Status |
|---|---|---|---|---|
| Open an incident, group issues across agents | Does it | — | — | Decided |
| Send alerts | Sends to channels, keeps them in the app and MCP | Sets up the channels; reads alerts | — | Decided |
| Investigate and contain (for example roll back) | Hands over the data fast | Does it | Pre-approves containment per agent | Proposed |
| Group failures into incidents | Does it | Corrects it (merge, split) | Corrects it | Decided 2026-11-12: grouping is the platform's job; a person or the assistant corrects it, and every correction is recorded |
| Close an incident | Records cause and reason | Proposes | Confirms | Decided |

## Improving over time

| Job | Connexity | Assistant | Person | Status |
|---|---|---|---|---|
| Build the roadmap (milestones and what is in them) | Stores it, shows it, measures progress | Writes it from issues, guided by Connexity's docs | Reorders in the app or through the assistant | Proposed, from the default rule |
| Fix issues | Verifies the fix, confirms it on real calls | Writes the fix | Approves | Decided |
| Weekly report | Produces and emails it | Reads it, updates the roadmap | Reads it | Decided |
| Talk to the client, settle business questions | — | — | Does it | Decided |

## Open questions

None right now.

## Offline approvals (Decided 2026-11-12)

- **An allow list, not a block list.** Connexity predefines the actions that may ever run without a person; a team can only switch those on. Anything not on the list always needs a person, so no "never list" is needed.
- **How it runs:** an incident opens, Connexity sends the alert to Slack, the assistant is instructed to check the agent's rules in Connexity through MCP and follow them (for example, roll back without approval if that is switched on).

- A person approves some actions in advance, per agent and per action; the assistant may propose additions, a person confirms. The policy lives in Connexity, so the gate's hook can check it and every offline action is recorded with its policy.
- **Incidents only, to start safe** (Dmytro 2026-11-12). Set on the Incidents page, Playbook tab: saved instructions for the assistant.
- **Flow:** Connexity opens an incident and alerts Slack; the assistant, if connected to that channel, picks it up, checks the rules in Connexity through MCP, and acts.
- **Each rule has two settings:** which agents it is allowed for, and a checkbox "Approve automatically". Unchecked, the assistant asks the person in its session before acting; checked, it goes ahead with no one (the 3 a.m. case).
- **Rules for now:** roll back to the last verified version; hotfix (write a fix and deploy it once it passes its tests in Connexity; never without passing them, Decided).
- **Clarifications are never answered without the person.** The assistant prepares answers and confirms them with the person in a batch, e.g. "I can answer 75 confidently; I need your help with the other 7."
- Every offline action shows afterwards in the incident timeline and the weekly report.
