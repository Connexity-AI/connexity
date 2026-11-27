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

1. **Code-based:** code over the trace, no model. Free and instant. *The tool returned
   an error. A dollar figure the agent said traces to no backend response, pre-call
   variable or anything the caller said.* ("Rule" means a spec rule only; Dmytro,
   2026-11-17.)
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

**The kind of check does not change severity** (Decided, Dmytro 2026-11-17). A check's
default comes from its issue type's "Default severity" in the Issue library, whatever
decides it. This replaces "a classifier or a judge defaults to flags". Each check shows its measured precision, from the findings people
confirmed and dismissed, as advice next to the setting. Measuring a judge against calls
a person labelled is designed when the first judge is built.

**A call is failed, degraded or clean.** Failed: at least one finding from a check set
to "fails the call". Degraded: findings, none of those. Clean: no findings.

- **Not graded** (Decided, Dmytro 2026-11-26, roadmap 105.11): a call where the agent
  spoke fewer than 10 words is never judged against the spec, whatever the kind of call.
  The floor counts the agent's words (`call.agent_words`, counted when the trace is
  stored), not seconds. With nothing found it is "not graded" instead of clean and
  counts in no score, so it cannot lift the score by looking like a call that passed. A
  finding a code check made on it still counts: the call stays failed or degraded,
  because that failure is real. One rule, `app/services/grading.py`, with its SQL twin
  `short_call()` in `app/crud/call_list.py`. A call whose checks have not run stays
  unchecked.

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
- **Category:** every issue belongs to the category its check declares, one of a fixed,
  Connexity-wide set kept in the `category` table (Decided 2026-11-12; built with
  `plans/2026-11-13-categories-table.md`). Code refers to a category by its stable
  `key`; the Connexity team edits names and order in the database. Spec rules will point
  at the same table.
- **Severity:** an issue is Critical when its check fails the call, otherwise a Warning.
- **Resolved:** the assistant or a person marks an issue fixed, linked to the version
  that carries the fix. There is no confirmation on real calls yet; if the issue happens
  again on a call that started after that, it reopens (Decided 2026-11-12). "After
  that" is when the version goes live: the first real call on it or on a higher number
  (Decided 2026-11-17, `plans/2026-11-17-mark-fixed.md`). Until then, calls on the old
  version never reopen it. A fix marked without a version counts from the moment it was
  marked. The assistant marks fixes with `mark_issue_fixed`, which refuses a version
  the issue was already found on.
- **Since the fix went live:** `get_issue` answers `since_version`: the agent's real
  calls that ran the fix's version or a later one, how many of them have the issue,
  and the newest of those (`plans/2026-11-21-verify-candidate-version.md`). A call
  counts by the version it ran (`version_reaches`), so a call an older version still
  served after the fix went live is left out. The `since_version` input asks the same
  for any version, also for an issue never marked fixed. Connexity gives the counts
  and never calls a fix confirmed. Open: a call on an older version that started after
  the fix went live still reopens the issue, because reopening goes by time, while
  these counts go by version.
- **Archived** replaces "accepted as known": the issue is real and nobody will fix it.
  - **Who:** a person, on the issue page or by saying yes when their assistant asks
    (`archive_issue`, recorded as "your assistant, approved by …"). It needs a reason
    and a duration: "until it spikes" (the default) or "forever".
  - **Hidden while archived** (Decided 2026-11-14, replacing "from that day; the past is
    never rewritten"): its findings are left out of every call's result, worst finding
    and findings, whatever the call's date. It makes no call fail and counts nothing
    toward the score, for the person and the assistant alike. It is still found and
    stored, and when it is unarchived, all its calls count again, including those from
    while it was archived. One rule, `shown_finding()` in `app/crud/check.py`, does
    this everywhere a call's result or findings are worked out.
  - **Spike:** an archived "until it spikes" issue comes back as reopened when, over the
    last 7 days, it hit at least 3 calls and at least twice the share of the agent's
    calls it had in the 30 days before the archive (any 3 calls if that was 0). The
    baseline is fixed when it is archived. It is checked as findings arrive. "Spike" is
    the word for this; "escalation" means handing a call to a person.
  - Every archive, unarchive and return is a decision record, and so is a resolved issue
    reopening, decided by Connexity.
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
arrive with the spec.

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

**Metrics.** Latency, cost, duration, time per tool. A threshold on a metric is a
code-based check ("the reply took over 2,000 ms"); the metric itself raises nothing.

**Not this product (Decided 2026-10-10).** Connexity verifies whether the agent did its
job correctly. It does not measure how much business that produced: conversion, revenue
and return on investment belong to a company's own analytics. The provider's call
analysis stays visible on the call, and data can be pulled out, but there is no outcome
rate and no outcome dashboard.

**How a check runs, by kind (built in roadmap 10.14).**

- **One shape for every kind** (`app/services/checks/base.py`). A check has a type, a
  version, its issue type's default and category, and a pure `run` that turns the
  trace into findings. A model check (`ModelCheck`) adds `ask`, its provider and its
  pinned model: `ask` puts its questions to the model, and `run` turns the stored
  answer and the trace into findings. A classifier asks typed questions (Jev,
  `services/jev.py`); a judge asks a language model (`checks/judge.py`).
- **Each check decides one way.** No shadow versions run in the product. Comparing two
  ways of deciding (an A/B test) happens outside the product, in a session, when
  Dmytro asks for it (Decided, Dmytro 2026-11-17).
- **Code-based checks run when a call is stored. Model checks run after,** in the
  scheduled call pull (`checks/model_checks.py`): until its model has answered, a
  model check is recorded as `pending` on the call and keeps the findings it had.
- **A model's answer is stored once per call and check version** (`model_answer`).
  Checking the call again reads it, so a re-check is free and cannot flip a finding by
  chance; a new version asks again. The answer holds labels keyed by event ids, never
  what was said.
- **A failed model call** is tried again on later passes and, after
  `MODEL_CHECK_MAX_ATTEMPTS` (3), the check is recorded as broke on that call. Broke
  never counts as clean. **No key** for the provider: the check is skipped, naming the
  missing setting.
- **A daily model budget for the whole product** (`MODEL_CHECKS_DAILY_BUDGET_USD`, $1;
  Decided, Dmytro 2026-11-17, an internal safety measure). When today's spend (UTC)
  reaches it, nothing more is asked until tomorrow and the calls stay pending.
- **Every finding says its kind,** shown as `found_by`: `code_based`, `classifier` or
  `judge`. A model finding's detail names the model.

**How a spec rule is checked (105.14).**

- **Each rule says how:** `classifier`, `classifier_then_llm` (the classifier raises,
  the LLM step confirms or dismisses, 105.16) or `llm`. The assistant sets it for now
  (Decided, Dmytro 2026-11-26). Code checks are Connexity's own and not a choice. A rule
  given none is `classifier`.
- **Each rule names the call inputs it needs,** at most 10, and a check is given only
  those, never all of them. In the lab, giving every rule every input moved 98
  unrelated answers; giving each only its own moved no more than the classifier's
  noise.
- **Short and long:** an input whose longest value on the agent's calls in the last 30
  days is over 200 characters is long (Decided, Dmytro 2026-11-26). Today that is the
  call history. The classifier gets only short inputs; the LLM step gets all of them.
  A rule that needs a long one cannot be `classifier`.
- **Never an input:** contact details, ids and secrets (Decided, Dmytro 2026-11-26),
  so no customer's email or number is sent to a model.
- **One way to read a rule:** `app/services/rule_context.py` gives every check the
  rule's text, its clarifications in force, its check type and its inputs' values on
  one call, with a fingerprint over all but the values.
- **Accepted weakness:** a strange call on a `classifier` rule is not verified.
  Marking false positives will reduce it later.

**The spec check (built in 105.15, `plans/2026-11-26-spec-check.md`).**

- **One model check, `spec_rule_broken`**, a classifier. It asks one yes or no question
  per rule in at most two requests: rules with no inputs with the call alone, and rules
  with inputs with the union of their short inputs (Decided, Dmytro 2026-11-26: "Two
  requests"). In the lab, two requests moved the other rules' answers no more than the
  classifier's own noise, at $0.21 per 1,000 observed minutes.
- **Bar:** 0.8 (Decided, Dmytro 2026-11-26). Every probability is stored with the rule's
  fingerprint, so a new bar needs no new model request.
- **`classifier_then_llm` flags go to the LLM step** (105.16), which confirms or
  dismisses each; until it answers, a flag raises nothing (Decided, Dmytro 2026-11-26).
  `llm` rules are judged by the LLM step alone, on every judged call.
- **Which calls:** real, graded (105.11), on an agent version a spec covers
  (`crud.spec_covering`). A check may say from the database whether it judges a call
  (`Check.applies`); a call it skips is recorded as skipped with the reason.
- **Judged once** (Decided, Dmytro 2026-11-26: "New calls only. In future we will have
  a way to rejudge - but explicitely only"). A later change to a rule judges the calls
  after it. From the check's release on, except that an agent's first spec written
  after the release judges its last 30 days once (Decided, Dmytro 2026-11-26: "First
  spec, 30 days"). Those findings are retroactive and count for nothing.
- **A finding on the whole call.** The classifier gives no moment and no reason
  (Decided, Dmytro 2026-11-26: "fine for now, we give reasoning only when we can"). The
  finding points at no event (`Check.whole_call`) and its key, the rule's, tells it
  apart. The screens and MCP say "no moment in the call" and give the probability.
- **One issue per rule,** keyed by the rule's key, in the rule's category, named after
  the rule (`issue.subject`). A critical rule's finding fails the call; any other only
  flags it (`Raised.flags_only`). Set to Flags, nothing fails; Off, nothing runs.

**The LLM step (built in 105.16, `plans/2026-11-27-llm-step.md`).**

- **Version 2 of the spec check,** not a new check: the same issue per rule and the
  same settings. The classifier asks first; then the LLM is asked about each
  `classifier_then_llm` rule the classifier scored at 0.8 or above, and each `llm`
  rule.
- **One rule per request** (Decided, Dmytro 2026-11-27: "I don't see reason not to do
  separate requests"; "lets start with separate for now"). A request holds the whole
  call, the inputs the rule names (long ones too), and last the rule with its
  clarifications, so a call's requests start the same way.
- **Never the prompt** (Decided, Dmytro 2026-11-27: "we use prompt only as
  prerequisite for spec, and then everything we do is 100% based on spec"). No other
  rule and no classifier score either.
- **The verdict** follows the test-run judge's shape: the reason, then the lines it
  rests on, then broken, kept or did not come up. Broken is a finding at those lines
  (the whole call when none are in it) with the reason. Kept or did not come up is
  stored and shown nowhere until false positives can be marked (105.17).
- **Who found it:** a confirmed flag is the classifier's finding, confirmed by the LLM
  (`detail.confirmed_by`); an `llm` rule's finding is a judge's.
- **The model:** Claude Haiku 5.5 to start (Decided, Dmytro 2026-11-27: "agree start
  with smaller"), set by `SPEC_LLM_MODEL` and `SPEC_LLM_PROVIDER`, priced by
  `checks/judge.py`. How good it is per kind of rule is lab work (Decided, Dmytro
  2026-11-27: "right now we just build the system").
- **A call is judged once:** a later version reads the answer an earlier one stored
  (`ModelCheck.answers_carry_over`) instead of asking again. Calls version 1 judged
  keep their findings, and their held flags stay held.
- **Without the LLM's key** the classifier part still counts; the flags it would
  confirm stay held and `llm` rules are not judged on that call. The answer names the
  missing setting (`llm_missing`).
- **Cost:** each `llm` rule is one more request on every judged call. Estimated from the
  lab's token counts, not measured: about $0.05 per 1,000 observed minutes to confirm
  flags, and $0.10 for each `llm` rule.

**False positives and dismissed flags (built in 105.17, `plans/2026-11-27-false-positives.md`).**

- **The path** (Dmytro: "1. Confirm with user 2. Create spec rule clarification 3.
  decide if keep issue and work on it or mark as false positive"):
  1. the assistant doubts an issue's findings and reads the calls;
  2. it asks the person what the rule means;
  3. it records the answer as a clarification, which judges new calls;
  4. it marks the old wrong findings, naming the clarification;
  5. it works on what is left.
- **A mark is on findings, many at once,** from any check (Decided, Dmytro 2026-11-27).
  Archive stays the action for a whole issue.
- **A marked finding counts nowhere:** not on its call, not in a result, score, size or
  chart (`counted_finding`, inside `shown_finding`). It stays stored, and checking the
  call again keeps the mark while the check raises the same finding.
- **Who may mark without asking:** the assistant marks without asking again when an
  answered clarification on the issue's own rule covers the findings. Otherwise the
  person approves in the conversation (`approved`): no clarification, a check with no
  spec rule, or a critical rule. Without it, the marking is refused and nothing
  changes (Decided, Dmytro 2026-11-27: "Refuse and say why").
- **Nothing changes for future calls** (Decided, Dmytro 2026-11-27). A wrong finding
  that keeps coming is fixed by a clarification, the check's setting, or archive.
- **Dismissed flags:**
  - A flag the LLM step dismissed is read from the stored answer.
  - Bringing it back records who did it on that answer, and the call is checked again.
    The classifier's flag then stands as a finding, without the model's reason
    (`detail.brought_back_by`).
  - A dismissed flag is listed only on its rule's issue.
- **Where it is seen:** the issue page counts both kinds and lists them under "Not
  counted", loaded only when opened (Decided, Dmytro 2026-11-27). Undo and Bring back
  are there. MCP has the same list (`get_issue` with `not_counted`) and the same undo
  (`undo_mark_false_positives`). Every marking, undo and bring-back is a decision on
  the issue (`findings_counted`), shown in its history.
- **An issue whose findings are all marked keeps its state** (Decided, Dmytro
  2026-11-27).

**Adding a check.** Dmytro names it in the Issue library. Then:

1. Pick the kind: code-based if code over the trace can decide it; a classifier if it
   splits into labelled facts plus code; a judge only when it cannot.
2. Write it as a draft and try it on real calls, read only, with
   `backend/scripts/try_check.py` (counts and ids only, a dollar cap). For an A/B test,
   run two drafts on the same calls and line them up with
   `backend/scripts/compare_runs.py`.
3. Register it in `checks/registry.py`, add its row to [`issue-types.md`](./issue-types.md)
   (a test fails without it), and test it on invented calls.

**Who makes checks.** Code-based checks ship with Connexity as a library with settings per
agent. Classifiers and judges are defined as data (a question, what counts as pass and
fail, which calls it applies to) by the assistant or a person. Checks written as code
from outside are postponed: configurable patterns first, sandboxed code last. A check the
assistant runs by itself and reports is ruled out, or advisory at most, because it would
be grading its own work.

Proposed, not yet confirmed:

- Titles follow Type, then Title, then Description. The type is fixed; the title
  describes the specific event and is filled from a template ("Booking tool returned an
  error"); no model writes it.
- "Resolved in a version" records the time and the version that carried the fix. A
  later finding reopens the issue when its call started after that version went live.
  Versions are ordered only when both are numbers, as Retell's are (2026-11-17).
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
- Team assignment, tentatively replaced by dispatch to the assistant (the inbox, a parked idea in the roadmap).
