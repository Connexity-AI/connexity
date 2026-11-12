# Checks, findings, issues and incidents

The model for what Connexity finds wrong on real calls, and how that becomes something a
person can act on. Decided with Dmytro on 2026-10-10 and refined since; the code in
`backend/app/services/checks/` and `backend/app/crud/check.py` implements the parts
built so far. The 2026-11-12 decisions (reopened and archived issues, incidents across
agents, alerts) are ahead of the code until their roadmap features are built. Each
statement is marked Decided, Proposed or Open. This is the model for real calls; tests
are designed separately and are not covered here.

| Concept | What it is |
|---|---|
| **Check** | Anything that looks at a call and can raise a finding. |
| **Fact** | Something derived from the trace and attached to a moment in it: an amount that was spoken, "the caller accepted". |
| **Finding** | One thing wrong at one moment in one call, raised by one version of one check. It points at exact events in the trace. |
| **Issue** | All findings with the same symptom on one agent. It lives forever. |
| **Incident** | One outage: a period during which an issue type was failing real calls, on one agent or several, with everything needed to respond to it, fix it and review it afterwards. |
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
come back after a release. An issue is open, resolved in a version, reopened, or
archived (Decided 2026-11-12, replacing "regressed" and "accepted as known"). The
cause is recorded on each incident.

- **Each occurrence is a finding** with its call and time; an issue's size is the number
  of calls it affected.
- **Severity:** an issue is Critical when its check fails the call, otherwise a Warning.
- **Resolved:** the assistant or a person marks an issue fixed, linked to the version
  that carries the fix. There is no confirmation on real calls yet; if the issue happens
  again on a call that started after that, it reopens (Decided 2026-11-12).
- **Archived** replaces "accepted as known": the issue is real and nobody will fix it. A
  person confirms it (the assistant may propose) with a reason and a duration, "until it
  gets worse" by default or "forever". It stops counting against the score, reliability
  and quality from that day, the charts are marked, and it comes back on its own when it
  gets worse. Every archive, unarchive and return is a decision record.
- **Every issue carries a tip** from Connexity: the likely cause and what to change.

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
arrive with the spec (the spec, Phase 3 in `REBUILD.md`).

**An incident is its own record: one outage that can span agents.** Every failed call
belongs to at least one incident, so a reliability figure can always be explained by
listing the incidents behind it. A call that fails for two issues belongs to both
incidents and is counted once (Decided 2026-10-10, replacing "exactly one").

- **It groups issues across agents by issue type and key** (Decided 2026-11-12,
  replacing "an incident belongs to one issue"): the same tool failing on ten agents is
  one incident covering ten issues, not ten incidents. It never groups by shared
  component. Merging and splitting incidents by hand is not built yet; whether to build
  it is Open.
- It **opens** on the first failed real call when no matching incident is active.
- It is **Active** or **Closed**. Closing an incident means the damage stopped (a
  rollback, a backend recovering, a workaround); resolving an issue means its cause was
  fixed. The two are separate (Decided 2026-11-12).
- It **closes** only when a person closes it, with how it stopped, the cause and a
  reason (Decided 2026-10-10, replacing "closes on evidence or after a quiet period").
  The assistant may propose closing; a person confirms. Nothing closes an incident
  automatically. Later there may be a queue of incidents that look fixed, for a person
  to confirm; not now.
- While it is open, further failed calls of the issue join it. After it is closed, a new
  failed call opens a new incident on the same issue, marked as a recurrence. "After" goes
  by when the call started: a failing call that started before the close and arrived
  late joins the closed incident without reopening it.
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
- "Resolved in a version" records the time and, as a note, the version that carried the
  fix. A later finding reopens the issue when its call started after that time. Ordering
  versions is not used (changed 2026-10-10 with manual closing).
- A person may later merge two issues, or split one by an attribute such as the kind of
  error.

**Alerts (Decided 2026-11-12).** Connexity sends incident alerts to the team's Slack
(Slack only to start): an incident opens, grows, comes back after closing, or closes.
Alerts are also kept in the app, as lines in the incident's timeline, so the assistant
can pull them through MCP. Active incidents need a person and are the most urgent thing
in the app; informational alerts never become to-do items.

Open:

- **Measures that are always slightly present, such as latency.** "Any reply over 2,000
  ms" never has a quiet period, so one incident collects thousands of findings and never
  closes. Three directions, none chosen: judge the call instead of the turn; open on a
  rise above the normal rate; split by what the agent was waiting on.
- **Shifts.** A notable change in a metric between two versions, with no single call at
  fault. Postponed until the foundation is solid.
- Team assignment, tentatively replaced by dispatch to the assistant (see the inbox in `REBUILD.md`, Phase 6).
