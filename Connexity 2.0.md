# Connexity 2.0

A planning document for the pivot. It records a design discussion between Dmytro and
Claude, held at the end of a two-month build of a production voice agent (an outbound
offer bot on Retell + n8n + GoHighLevel). The lessons from that build are included as
the first case study. It is one example, not the definition of the product: more case
studies on other stacks will be added, and nothing here should be read as specific to
this stack or this use case.

Each section is marked:

- **Decided** — Dmytro stated this explicitly.
- **Proposed** — Claude's suggestion, discussed but not explicitly confirmed.
- **Open** — not settled.

---

## 1. The idea in one paragraph

Voice agent development can be close to fully automatic if three roles are kept
separate. An AI assistant (Claude Code or any other) does the engineering. The product
is the system of record and the independent verifier. The human makes business
decisions and approves changes. Connexity 2.0 is the product in that picture. It holds
the spec, the call traces, the versions, and the test verdicts. It checks every real
call, detects incidents, and tells the human what needs a decision. It never writes
fixes and it never talks back.

**Target user (Decided):** teams that are aggressive about AI and already work through
an assistant. The product is not built for teams that want to deploy by hand, and it
does not try to serve everyone.

---

## 2. Evidence: what went wrong on a real build

**Case study 1: an outbound offer bot (Retell + n8n + GoHighLevel).** These are the
problems that consumed the most time on that project. Each one maps to a product
capability below. Further case studies on other stacks will be added to this section.

1. **Test verdicts were the least reliable part of the system.** The two worst bugs
   (the agent collapsing several turns into one monologue with stage directions read
   aloud, and the agent hanging up on a seller who had just said yes to a referral)
   were inside test cases the judge scored as passing. The same unchanged transcript
   got pass, fail, pass across three consecutive runs. Most failures were bad metrics
   or broken personas, not agent behaviour. Real bugs were found by reading transcripts
   and by simple structural checks.

2. **The test suite went stale.** Metrics kept asserting an old rule after the rule
   changed, so one test passed on broken behaviour and failed on the fix. Mocks
   returned values that had stopped being normal. Simulated callers broke character or
   looped until the simulator cut the call.

3. **Nobody knew exactly which version was being tested.** Client feedback predated
   fixes. The agent showed as unpublished while serving calls. A backend fix was
   committed while the live n8n node still ran old code, and three of five real calls
   failed on logic that "was fixed".

4. **Root cause required joining four systems by hand.** Transcript, tool payloads,
   dynamic variables, and the n8n execution. A reported "price dropped from 275 to 262"
   looked like a backend bug and was a hallucination: the agent invented 275 while the
   backend call was still running.

5. **Fixes broke failure paths.** Twice a correct main-path fix broke the degraded
   path: the agent invented a price when the backend returned nothing, and an accepted
   price went up after a confirmation step.

6. **Prompt rules failed on the things that cost money.** "Never raise a price the
   seller already accepted" was a prompt rule and did not hold; the deal closed 11k
   higher. The fix was to enforce it in backend code. A sweep of backend edge cases,
   with no conversation involved, found three critical bugs in minutes that 22
   conversational tests had missed (including offering up to 69k more than the seller
   asked for).

7. **Client intent was the hardest input.** Feedback arrived as chat messages, out of
   order and often ambiguous. Claude once recorded the client as agreeing to a design
   he had only restated a concern about. Who decided what, and when, was stored nowhere.

8. **Security problems were information-flow problems.** A credential was picked up
   from a sibling project. The backend webhook had no authentication. Internal
   negotiation reasoning was returned to the model, where the agent could repeat it to
   a seller. Test data could reach real sellers through a fallback.

9. **The test harness itself was faulty.** Every simulated call shared one call ID, and
   batches ran concurrently, so one test read another test's stored state. Some results
   reported as verified were contaminated.

10. **Some failures only exist on live calls.** Phone call screeners, people talking
    during a hold, transcription errors on dollar amounts. Text simulation cannot
    produce them.

---

## 3. The three roles (Decided)

| | Owns | Never does |
|---|---|---|
| **Product** | Spec and decisions, call traces, versions, test execution and verdicts, incident detection, the inbox | Write fixes. Hold a conversation. |
| **Assistant** | Investigating, writing changes across prompt, backend and tests, deploying, connecting tools | Approve its own work. Be the system of record. |
| **Human** | Business decisions, approvals, the client relationship | Read raw transcripts to find bugs, write tests by hand, work out which version a call ran on |

The central rule: **the assistant never grades its own work.** It proposes and deploys.
The product runs the checks and produces the verdicts.

---

## 4. No chat in the product (Decided)

Nothing in the product talks back. Chat means the user's own assistant, and the user
should never be unsure about that.

Nothing the user types gets a reply. The places that matter most are:

- a comment on a moment in a call
- an answer to a decision question
- an edit to a spec rule

Forms for what Connexity itself holds (connections, agents and their links, and later
spec rules, tests, judges and checks) are allowed: the UI may do anything the assistant
can do through the API (Decided 2026-10-09). They are forms, not conversation.

The product's own use of models (triage, judges, classifiers) is background work. Its
output is always an artifact: an issue, a diff, a verification result, a spec entry.

### Linking the product and the assistant (Proposed)

- **Focus sharing.** The product tracks what the user is looking at (open call,
  playback position, selected lines) and exposes it as a tool. The user switches to the
  assistant and asks "why did it say this?" with no copying.
- **Navigate back.** The assistant can move the product view to a specific call moment
  when it answers.
- **Pins.** The user pins moments across calls, then asks the assistant about the set.
- **Conclusions return to the product.** A finding reached in chat is saved as a note
  or an issue, so it outlives the conversation.
- **One-click "ask assistant"** where the assistant supports prefilled links.
- **Product views inside the chat** (a call player, a diff with an approve button),
  where the assistant supports embedded tool interfaces. Later step.

Avoid an "@assistant" mention inside product comments. It reintroduces chat.

---

## 5. Connections and secrets (Decided)

- Secrets live in the assistant's workspace `.env`, per agent.
- The assistant connects to the voice platform, the backend and the CRM directly. It
  does not proxy through the product.
- The assistant connects the product to those tools, not the other way round.
- The product must have **read access** to everything, so it can ingest calls and
  detect drift when no assistant session is open.
- The product must **highlight any bypass**: a change that went live without passing
  verification.

Setup flow: the user asks the assistant to set up the product. The assistant asks which
tools they use, finds or requests the keys in `.env` (the user fills in the file; keys
are not pasted into chat), tests each connection, and offers to register them with the
product.

Consequences (Proposed):

- The deploy gate is a convention, enforced by a pre-deploy hook in the workspace and
  by the assistant's standing instructions. It is not enforced by the product holding
  access.
- Keys exist in two places, so rotation must update both.

### Bypass detection (Proposed)

- The product stores a fingerprint of each verified state: flow, prompts, skill code,
  agent settings.
- It polls live state and compares.
- Every incoming call carries the version that served it. A call on an unverified
  version is flagged at once and stays marked permanently.
- An alert says what changed, when it was first seen, how many calls ran on it, and
  offers verify or roll back.
- It distinguishes three cases: an unverified deploy by the assistant, a manual edit in
  a provider dashboard, and a partial deploy (one piece shipped without the other).
  The partial deploy ranks highest.

---

## 6. The spec (Proposed, with spec editing Decided)

The spec is the single source of truth: the agent's business rules in plain language.
Each rule records who decided it, when, and from which source message.

- Prompts, tests and backend guards are derived from the spec.
- Every test links to a rule. The product shows coverage: rules with no test, and tests
  with no rule.
- When a rule changes, its tests are marked stale and regenerated.
- **Enforcement placement.** For each rule the product asks whether it concerns money,
  safety or compliance. If so, it belongs in deterministic code. A money rule enforced
  only by the prompt is flagged.
- The assistant can propose "the client decided X" only with linked evidence. The
  client's exact words are stored with the decision.

**Decided:** the user can edit spec rules directly in the UI. Whether to allow other
editing is deferred.

---

## 7. Verification

### Checks, findings, issues and incidents (Decided 2026-10-10)

This is the model for real calls. Tests, the inbox and alerting are designed separately
and are not covered here.

| Concept | What it is |
|---|---|
| **Check** | Anything that looks at a call and can raise a finding. |
| **Fact** | Something derived from the trace and attached to a moment in it: an amount that was spoken, "the caller accepted". |
| **Finding** | One thing wrong at one moment in one call, raised by one version of one check. It points at exact events in the trace. |
| **Issue** | All findings with the same symptom on one agent. It lives forever. |
| **Incident** | A period during which an issue was failing real calls, with everything needed to respond to it, fix it and review it afterwards. |
| **Metric** | A number measured on a call. It has no pass or fail. |
| **Decision record** | Who decided what, when and why. |

**Checks.** One concept with three kinds, by how the check decides:

1. **Rule:** code over the trace, no model. Free and instant. *The tool returned an
   error. A dollar figure the agent said traces to no backend response, pre-call
   variable or anything the caller said.*
2. **Classifier:** a small model returns one label from a fixed set. *Did the caller
   accept, counter or defer? Is the other party a person, a call screener or
   voicemail?*
3. **Judge:** a language model answers one question against written criteria. Only for
   qualitative questions.

- There is no separate "rubric". A rubric is a list of questions; each question is its
  own check.
- **No check produces a score.** A judge returns pass or fail, the moments in the call
  it relied on, and a short reason. A pass or fail can be compared with a person's
  answer; a number out of 100 cannot.
- **Checks are rules over events and facts.** Most classifiers produce facts, and a rule
  turns facts into a finding. A finding is only as reliable as the least reliable fact
  it used.
- **Every finding comes from a named check looking for a named thing.** An open-ended
  "find anything wrong with this call" pass cannot raise findings. It may exist later as
  discovery, whose output is a proposal for a new check that a person accepts.
- A person can report a finding by hand, on a moment in a call.

**Per agent, each check is off, flags, or fails the call.** The user decides.

| Setting | Effect |
|---|---|
| Off | Does not run. |
| Flags | Raises findings and issues. The call is not failed. |
| Fails the call | A finding marks the call failed and belongs to an incident. |

A rule check is tested code, so its default comes from its type. A classifier or a judge
defaults to "flags". Each check shows its measured precision, from the findings people
confirmed and dismissed, as advice next to the setting. Measuring a judge against calls
a person labelled is designed when the first judge is built.

**A call is failed, degraded or clean.** Failed: at least one finding from a check set
to "fails the call". Degraded: findings, none of those. Clean: no findings.

- **Reliability** is the share of production calls that are not failed. Calls that never
  connected or reached voicemail are left out.
- **Quality** is the share that are clean.
- Both are shown per agent and per version. Neither rewrites the past (see decision
  records).

**An issue is identified by its symptom, not its cause.** Its identity is the agent, the
issue type, and a key the type defines, usually the one thing that says what broke (the
tool's name, the rule). The version, whether the call was a test, and the error text are
not part of it, so the same issue can be found in a test and on a real call, and can
come back after a release. An issue is open, resolved in a version, regressed, or
accepted as known. The cause is recorded on each incident.

Starting types. The first group is true under any prompt and is what Phase 2 builds.
The second group depends on what the agent was instructed to do, so it waits for the
spec (Decided 2026-10-10, after trying the checks on real calls).

| Type | Key | Fails the call by default |
|---|---|---|
| Tool call failed, including a failed step inside the backend | Tool name | Yes |
| Tool call got no result | Tool name | Yes |
| Agent stopped responding | None | Yes |
| Same thing said twice | None | No |
| Stage directions spoken aloud | None | No |
| Slow response | None | No, and only a flag until the open item on latency is settled |

| Type, with the spec | Key | Why it waits |
|---|---|---|
| Value spoken that came from nowhere | Kind of value | Whether a value is legitimate depends on what the prompt or a rule allows. On one real agent, 370 of 385 spoken amounts were written in the prompt. |
| Value spoken before the tool answered | Tool name | Needs the same matching of values. |
| Two questions in one turn | None | A style rule, not a defect under every prompt. |
| Agent ended the call early | None | Needs to know when the agent is meant to end; a caller speaking last is how a normal goodbye looks. |
| Spec rule broken | The rule | Set per rule. |

Where "two questions in one turn" belongs, and whether "same thing said twice" and
"stage directions" stay in the first group, is Claude's split; Dmytro has not confirmed
those three.

Business issue types are the customer's own spec rules, not a fixed list of codes. They
arrive with the spec (section 6).

**An incident is its own record, and an issue can have many.** Every failed call belongs
to exactly one incident, so a reliability figure can always be explained by listing the
incidents behind it.

- It **opens** on the first failed real call of an issue that has no open incident.
- It **closes** when real calls on the fixed version have passed without it, or after a
  quiet period, which is recorded as "stopped without a fix". Never on a click alone.
- If it comes back before the fix was confirmed, the same incident continues. If it
  comes back after a confirmed close, a new incident opens on the same issue and is
  marked as a recurrence.
- It holds what is needed for **response** (the calls and callers affected, the versions
  and tools involved, the evidence, and what changed just before it started), for
  **remediation** (what was done, by whom, the version that carried the fix, whether it
  was confirmed), and for the **post-mortem** (a timeline, time to detect and to
  resolve, the cause, and what came out of it).
- Issues from checks that only flag never become incidents.

**Decision records.** Every change to what a check does for an agent, every finding
dismissed as wrong, every incident declared by hand and every resolution is recorded:
who, when, what it applied to, the old and new value, and a reason.

- A decision takes effect when it is made. It never rewrites past reliability; the chart
  is marked at that date. The same mark is used when a check is added.
- The assistant may propose a decision that changes the number; a person confirms it.
- A reason is required when the change makes the number better.

**Metrics.** Latency, cost, duration, time per tool. A threshold on a metric is a rule
check ("the reply took over 2,000 ms"); the metric itself raises nothing.

**Not this product (Decided 2026-10-10).** Connexity verifies whether the agent did its
job correctly. It does not measure how much business that produced: conversion, revenue
and return on investment belong to a company's own analytics. The provider's call
analysis stays visible on the call, and data can be pulled out, but there is no outcome
rate and no outcome dashboard.

**Who makes checks.** Rule checks ship with Connexity as a library with settings per
agent. Classifiers and judges are defined as data (a question, what counts as pass and
fail, which calls it applies to) by the assistant or a person. Checks written as code
from outside are postponed: configurable patterns first, sandboxed code last. A check the
assistant runs by itself and reports is ruled out, or advisory at most, because it would
be grading its own work.

Proposed, not yet confirmed:

- Titles follow Type, then Title, then Description. The type is fixed; the title
  describes the specific event and is filled from a template ("Booking tool returned an
  error"); no model writes it.
- "Resolved in a version" records the time and the component version that carried the
  fix. A later finding is a regression only if its call ran on that version or a later
  one; versions are ordered by when they were first seen.
- A person may later merge two issues, or split one by an attribute such as the kind of
  error.

Open:

- **Measures that are always slightly present, such as latency.** "Any reply over 2,000
  ms" never has a quiet period, so one incident collects thousands of findings and never
  closes. Three directions, none chosen: judge the call instead of the turn; open on a
  rise above the normal rate; split by what the agent was waiting on.
- **Shifts.** A notable change in a metric between two versions, with no single call at
  fault. Postponed until the foundation is solid.
- Team assignment, tentatively replaced by dispatch to the assistant (section 11).

**About Jev.** A model from TypeSafe AI that returns typed decisions with probabilities
and does not generate text. Reported as roughly 100 ms to half a second per decision,
far cheaper than language-model judges, and consistent across runs, with accuracy
similar to large models on the datasets cited. Two cautions: consistent is not the same
as correct, so calibration is still required; and competitors in voice evaluation are
already adopting it, so it is not a differentiator on its own. (Source: web search
summaries, October 2026; the articles were not read in full.)

### Who creates and who verifies (Proposed)

The assistant creates tests, judges and classifiers through the product's API: models,
rubrics, labels, thresholds. The product stores, validates, runs and judges.

- **Tests are validated on submission:** looping personas, stale mocks, ambiguous
  metrics.
- **Judges are measured before they count:** agreement with human-labelled calls, and
  stability across repeated runs. A judge starts as "flags"; the user decides when it
  may fail a call, with the measurements as advice.
- **Changes to tests and judges are reviewed like changes to the agent.** If a fix also
  loosens a metric or a rubric, the review shows the before and after and the user
  approves it explicitly.
- **Harness integrity:** the product detects state shared between tests and test
  traffic reaching production data.

### Backend edge-case testing (Proposed)

The product tests each skill as a black box against the spec's rules, across a range of
inputs, with no conversation. Most money bugs in case study 1 were found this
way.

### Change-impact regression (Proposed)

When a node or skill changes, tests are run for every path it touches, failure paths
especially, before deploy.

---

## 8. Skills and the CRM: always attached to an agent (Decided)

The agent is central. A workflow or a CRM record exists in the product only as
something an agent used. It is not possible to test a workflow or browse the CRM
without an agent.

This is a rule about the entry point, not about depth. Technical depth is wanted: a
voice engineer must be able to recognise an issue instantly.

**Path:** agent → call → tool call → n8n execution → node-by-node detail.

In scope:

- Full execution detail for every tool call, attached to the call that triggered it.
- Skill tests that belong to an agent and run against its spec rules.
- Per-call CRM data: what came in, what was written back, and the later outcome.
- Versions of every skill the agent uses, as part of its verified state.

Out of scope:

- A list of all workflows in an account.
- Running or testing a workflow no agent uses.
- Browsing CRM records unrelated to a call.
- General observability for n8n. Connexity is not Langfuse.

A workflow shared by several agents appears under each one. A change to it re-verifies
every agent attached.

### CRM checks (Proposed)

1. **Before the call:** the data the agent needs is present, plausible and internally
   consistent.
2. **After the call:** what the spec says must be written has landed. Failures are
   "nothing landed", "landed incomplete" and "landed wrong". Checked after a short
   delay, because writes are usually asynchronous.
3. **Later:** the deal outcome, used to measure the agent in business terms.

---

## 9. Provider strategy (Decided)

- **Ingestion is provider-agnostic.** Connexity defines a schema. The assistant writes
  the mapping from a provider (Retell, Vapi, Pipecat, others) to that schema.
- **Evaluation is not provider-agnostic.** Running the same model outside the
  agent's real stack gives very different results, so simulations must run on the
  agent's own engine: the provider's engine for hosted platforms (Retell, Vapi), and
  the team's own deployed service for self-hosted frameworks (Pipecat and similar),
  reached through a Connexity-defined endpoint contract. Connexity never re-implements
  an agent from a copy of its prompt. The connectors and the contract are built once
  and supported by the Connexity team. Doing it per session from the assistant is too
  fragile.

Result: observability works with any provider, and testing works with supported
providers.

Supporting detail (Proposed):

- The mapping is a saved artifact that runs without an assistant session (provider
  webhook to an ingest endpoint, or scheduled pull).
- The product runs a conformance check on the mapping and reports which capabilities it
  enables. Checks degrade by capability.
- Mapping health is checked on every ingest, so a provider API change raises an item.
- The schema has a small required core (call, turns, tool calls with arguments and
  results, input variables, component versions) and optional extensions. Unmapped data
  is kept raw.
- The test definition in Connexity is provider-neutral. Connectors translate it.
- Verified reference mappings are published for the most common providers.

---

## 10. Client feedback (Decided in direction)

Clients cannot be moved onto a new tool. They send feedback through Slack, email,
Upwork and meeting notes, and that will not change. Agencies also tend to build their
own client-facing platforms.

- No client portal is planned. One may come later for reporting.
- Feedback enters through the user's assistant (Proposed): the user hands over the raw
  text, the assistant splits it into items and matches each to calls and versions, the
  client's exact words, source and date are stored, and the user confirms the matches.
- The assistant drafts replies and questions for the client. The user sends them
  through their existing channel.
- A reporting API for agencies' own dashboards (Proposed).

---

## 11. The inbox (Decided as the core paradigm)

Human-in-the-loop is the core of the product, and the inbox is the home screen. It
must be powerful enough for users to decide what is urgent, where alerts go, and what
goes to the assistant.

Controls (Proposed):

- **Priority** per item type, adjustable per agent.
- **Routing rules:** stay for a human, go to the assistant first, apply automatically
  and report, or also notify an outside channel.
- **Approval policy** by risk: test-only fixes automatic, prompt changes one click,
  money rules require a recorded decision.
- **Grouping:** many calls failing the same check become one item.
- **Snooze and digest** for low-priority items.

### Assistant dispatch (Decided: the user chooses)

Some teams want full automation: incident, instant trigger to the assistant, a tested
solution waiting for the user. Others want to trigger the assistant themselves. This is
a setting, per agent and per item type.

| Mode | When an item arrives |
|---|---|
| **Manual** | It waits. The user opens a session and assigns it. |
| **Investigate** | A session starts automatically, diagnoses, and attaches findings. No changes. |
| **Prepare** | The assistant diagnoses and writes the fix, the product verifies it, and the user decides whether to deploy. |

Deploy stays with the human in all three. Mode names are proposed.

Requirements for the automatic modes (Proposed): somewhere for the session to run with
access to the workspace secrets, grouping before dispatch, a session cap and spending
limit, a full record of what the assistant did unattended, and a fallback to a manual
item if the session fails.

---

## 12. Incident response (Decided: a crucial role of the app, and part of onboarding)

An incident is a period during which an issue is failing real calls, kept as its own
record with what is needed to respond, to fix and to review afterwards. The model is in
section 7 (Decided 2026-10-10).

The earlier severity table is withdrawn. Whether a problem is an incident is no longer a
matter of severity: it follows from the check being set to "fails the call". Two of its
rows were not incidents under this model. A spike in a check that only flags is an
escalation of an issue. A sudden drop in outcomes has no single call at fault; it is a
shift in a metric, which is postponed, and business outcomes are outside the product.
Who is told about what, and how fast, is alerting, which is designed separately.

Lifecycle (Proposed): detect, group, size the exposure, contain, diagnose and fix,
verify and deploy, confirm on the next real calls, close with a new rule or test.

**Containment (Proposed).** The product has read access only, so it cannot roll back or
pause calls itself. During onboarding the user pre-approves containment actions per
severity, for example "on a critical incident the assistant may roll back to the last
verified version, then notify me."

**Onboarding (Proposed).** The assistant walks the user through an incident policy per
agent: severities, who is notified and where, dispatch mode per severity, pre-approved
containment, where automatic sessions run, and limits. Onboarding ends with a fire
drill: a simulated incident that exercises the whole chain. Onboarding is complete when
the drill passes.

---

## 13. Onboarding (Decided: it starts in the assistant)

Onboarding begins in the user's assistant. AI-native docs let a session pull everything
it needs about the product. The product is one part of a larger harness, and users are
either new or already have their own development lifecycle.

Design (Proposed):

- The product tracks onboarding state and tells the assistant the next step.
- Docs are served by task as short playbooks. Every step has a verify call. Playbooks
  skip what is already done and include explicit don'ts.
- The first step is read-only and delivers value before any restructuring.

### The recommended model: a ladder (Proposed)

| Level | What the user gets |
|---|---|
| 1. Observe | Every call as one joined trace, with versions |
| 2. Check | Deterministic checks on every call |
| 3. Spec | Business rules with provenance |
| 4. Test | Simulations and backend tests derived from the spec |
| 5. Gate | Verified deploys and bypass detection |
| 6. Loop | Automatic triage and prepared fixes |

- **Teams with a lifecycle:** the assistant audits the repo and accounts, places them
  on the ladder, and adopts their setup in place.
- **New teams:** the assistant scaffolds a reference setup: repo layout, default house
  rules with reasons, and a standing instruction file so every later session follows
  the same lifecycle.

Default house rules, so far drawn from case study 1:

1. The agent does no arithmetic and makes no decisions. It calls a skill and speaks the
   result.
2. Failure paths never close. A failed backend call routes to a human.
3. One question per turn. No stage directions aloud. No words in the caller's mouth.
4. Money-critical rules are enforced in code.
5. Extract after the call, not during it.

---

## 14. What working on an agent looks like (Proposed)

1. The user briefs the assistant with whatever exists: a script, a recording, notes.
2. The assistant drafts the spec and a list of open questions.
3. The questions arrive in the inbox. Answers become rules.
4. The assistant builds the flow, prompts and skills.
5. The assistant writes tests from the spec. The product validates and runs them.
6. The user asks the assistant to place test calls (Decided: through the assistant
   only, and only on explicit request).
7. Client feedback comes in through the assistant and becomes items tied to calls.
8. Each item is triaged, fixed, verified and approved.
9. In production, the product checks every call and raises items and incidents.

For an existing agent, the assistant derives the spec from the current prompts and
skills, and the first findings come from running checks over past calls.

---

## 15. UI structure

**Principle (Proposed):** the UI is for seeing and deciding. Creating and editing
happen through the assistant.

**Home (Decided):** the inbox.

Inside an agent (Proposed):

- **Inbox:** approvals, decision questions, bypass alerts, incidents, failed checks.
  One screen per item with evidence, the proposed change, the verification result and
  the action. Open incidents sit at the top.
- **Calls:** audio and transcript, each tool call expandable to the node-by-node
  execution, CRM data in and out, the version of each component and whether it was
  verified, check results on the exact turns. Comment, pin, or pick up in the assistant.
- **Spec:** rules with who decided them, where they are enforced, and test coverage.
  Editable.
- **Tests:** results grouped by spec rule, with verdict stability. Judges and
  classifiers with calibration status.
- **Versions:** a timeline of changes across prompt, skills and tests, with approvals,
  verification results, bypasses and rollback.
- **Overview:** reliability and quality per version, with the incidents behind them.
  Not business outcomes (section 7).

Not in the UI: a chat box, editors for the agent's prompts or workflows, anything that
deploys or writes to a provider, AI that generates content inside the product (an
internal assistant, test case generation), any top-level section for workflows or the
CRM. Otherwise the UI may do whatever the assistant can do through the API, including
setting up connections (Decided 2026-10-09).

---

## 16. What Connexity 2.0 is not

- A chat assistant.
- A workflow builder, a CRM, or a proxy to them.
- General observability for n8n or any backend.
- A deploy pipeline. The assistant deploys.
- A simulator that replaces the agent's own engine.
- A product for teams that deploy manually.
- Business analytics. Conversion, revenue and return on investment belong to a
  company's own tools.

Test for any future feature: does it describe an agent's conversation, or something
that conversation touched? If yes, it can belong. If it describes another system on its
own, it belongs to the assistant and that system's tools.

---

## 17. Where the moat is (Claude's view)

Generating prompts, fixes and tests is close to solved. Eval runners and simulators are
becoming commodities; providers ship their own. Two things are not solved:

1. Knowing what the client actually decided.
2. Knowing whether a verdict is true.

The durable value is the spec with provenance, verification that can be trusted, and
incident response, joined across every system the agent touches.

---

## 18. Open questions

1. Where automatic assistant sessions run: a cloud agent, a CI job, or a local runner.
   The secrets are in the workspace, so the session must run where the workspace is.
2. Which providers get first-party test connectors first.
3. Whether the product runs backend edge-case tests itself or accepts results from the
   assistant. Claude recommends the product runs them.
4. Whether to offer a reporting API or a client portal, and when.
5. Whether automatic deploy ever becomes a dispatch mode for low-risk items.
6. Which parts of the previous Connexity product carry over. It was deliberately not
   discussed, to avoid anchoring this design.
7. How live-only failures are tested: replay of recorded calls or audio-level
   simulation.
8. Key rotation across the workspace and the product.
