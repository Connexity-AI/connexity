# Clarifications, part 1: schema and logic

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Clarifications in Action items" (10.12),
  part 1 of 3. Split like the spec (Decided, Dmytro: "start with schema and logic
  so we can discuss it ... then MCP and frontend are derivatives"):
  1. **Schema and logic** (this plan): the table, its states, and what raising,
     answering and parking do to the spec, tested through the service layer.
  2. **MCP:** the assistant raises, lists and answers (demo step 4: answered in Claude
     Code). A thin layer over part 1.
  3. **Action items page** after the demo, from `designs/03-action-items-and-spec.md`
     (the Action items part), `designs/12-adjustments.md` item 5 and
     `designs/screens/Connexity Action items.dc.html`.
- **Design:** no UI change.
- **MCP:** none in this part. Nothing a user or the assistant can reach changes until
  part 2, which follows straight after. Part 2 adds the tools and rewrites the spec
  guide's "Raise these as clarifications" section.

## Goal

Connexity can hold a question about an agent's behaviour that its spec does not settle,
with fixed answers, and turn the chosen answer into a spec rule in a new spec version.
That rule is carried into every later version and is never quietly dropped. Parts 2 and
3 only expose this.

## What exists

- **Specs** (#199, #200): versions per agent, and rules are never edited. A new agent
  version adopts the previous spec (`adopt_spec_safely`). `write_spec` writes a version
  under the agent lock (`lock_agent`).
- **`spec_rule.source`** already has `clarification`, and **`spec_rule.clarification_id`**
  is a plain id waiting for this table.
- **`write_spec`** sets every rule's source to `prompt` and needs a quote for each.
- **Decision records** keep who decided what: the person (`decided_by`) and the assistant
  that acted for them.

## Changes

### A clarification

One row per question, on one agent:

| Field | What it holds |
|---|---|
| question | One plain sentence: "The agent changed an existing appointment on 9 calls. Is it allowed to?" |
| answers | Two to four (a to d), each a short **label** ("Only when the caller asks") and the **rule** it becomes ("Change an existing appointment only when the caller asks for it") (question 1) |
| category, touches | The rule's category (one of the fixed ones) and money, safety, compliance or none |
| calls | The calls where the behaviour was seen, 0 to 50, all the agent's own (question 2; empty for trigger 2) |
| spec | The spec version it was raised against (question 3) |
| replaces | Optionally, the key of a rule in that spec that the answer replaces (question 4) |
| state | open, answered or parked |
| answer | The chosen answer (a to d) and the spec version it made |
| who | Who raised, answered or parked it, the assistant that acted, and when |

### States

```
raise ──> open ──answer──> answered   (final, question 5)
           │  ↑
          park │ answer
           ↓  │
          parked
```

- **Raise:** stores the question open. It is refused, listing every problem and storing
  nothing, when:
  - the agent has no spec;
  - a text is empty or over 500 characters;
  - there are fewer than 2 or more than 4 answers;
  - the category is unknown;
  - a call is not the agent's;
  - a replaced key is not in the agent's latest spec;
  - an open or parked question on the agent has the same text (case and punctuation
    ignored).
  Several questions for one agent go in at once, all or nothing.
- **Answer:** an open or parked question can be answered. An answered one cannot.
- **Park:** an open question can be parked. A parked one can still be answered, which
  is how it is reopened.

### What an answer does to the spec

- **Answers for one agent, given together, make one new spec version.** It holds the
  latest version's rules, plus one rule per answer.
- **Each new rule** has source `clarification`, the clarification's id, the chosen
  answer's rule as its text, and the clarification's category and `touches`.
- **A replacing answer** drops the rule it replaces. The new rule takes that rule's key,
  so comparing versions shows it as changed in place.
- **The new version** keeps the agent version of the latest spec. It records who answered
  and the assistant, and its origin is a new value, `answered`, so the history says why
  the version exists.
- **It is written under the agent lock,** like `write_spec` and adoption, so two writes
  never take the same number.
- **Parking** creates no spec version.
- **Each answer and each park is a decision record** (new kinds `clarification_answered`
  and `clarification_parked`).

### Rules from answers are carried over (question 4)

- **Adoption** already copies every rule, these included.
- **`write_spec`** rewrites the prompt's rules only. Every rule from a clarification is
  carried into the new version unchanged, with its key. Passing one in is refused, so a
  rewrite can never drop or reword a person's answer. To change one, a new clarification
  replaces it.

### Spec state

- An `answered` version counts as current, like a written one, while the agent stays on
  its version.
- An agent's open count comes from a query that parts 2 and 3 use: open per agent and
  for the workspace.

### Data

- **New table `clarification`** (migration `0021_clarification`). It has `company_id`,
  the agent (cascade), the spec it was raised against (set null), and the category
  (restrict). The answers are a JSON list of label and rule. The call ids are a JSON
  list, so a deleted call does not delete the question (Proposed). It holds the state,
  the replaced key and the chosen answer, plus the spec version made (set null), and
  who and when for raising, answering and parking.
- **`spec_rule.clarification_id`** gains its foreign key, with `SET NULL`.
- **`SpecOrigin`** gains `answered`. **`DecisionKind`** gains the two kinds above.
- **The table is not the assistant's alone.** Connexity will raise clarifications from
  calls later (spec drift, Decided 2026-11-12). The same raise works for it, with
  "Connexity" as who raised.

## Decisions

- **Multiple choice a to d, answers become spec rules, and the assistant confirms answers
  with the person in a batch.** Decided (2026-11-11).
- **No criticality yet.** `touches` comes from the spec. There is no severity or
  ranking. Decided (2026-11-11).
- **The person and the assistant can both park.** Decided (`designs/who-does-what.md`).
- **Schema and logic first, then MCP, then the page.** Decided, from Dmytro's comment
  above.
- The answers to the questions and the triggers are below.

## Questions

Answered by Dmytro, 2026-11-15: "1. ok 2. ok but question - what triggers clarification
creation? 3. yes 4. yes 5. yes 6. it can be parked or user can delegate decision to ai
assistant but on the backend it should be either answered or parked or open".

1. **Each answer carries its rule, written when the question is raised.** Decided.
2. **Evidence is a list of calls, and its count is what is shown.** Decided. The list may
   be empty, for a question raised from a prompt change ("What raises a clarification").
3. **No clarifications before the agent has a spec.** Decided.
4. **Answered rules survive `write_spec` and change only through a replacing
   clarification.** Decided.
5. **Answered is final.** Decided.
6. **Every answer becomes a rule; there is no "doesn't matter".** Decided. The person may
   park it, or let the assistant decide. On the backend, a decision the person handed to
   the assistant is an answer like any other: answered, with the person and the
   assistant recorded. The state is only ever open, answered or parked.

## What raises a clarification

Connexity does not raise them itself yet. That is spec drift, detected on real calls,
later (Decided 2026-11-12). Until then the assistant raises them, and Connexity's next
steps tell it when. All three triggers are Decided (Dmytro, 2026-11-15: "Accept all
three"):

1. **Writing the first spec.** The assistant reads the prompt and recent calls. Behaviour
   seen on calls that the prompt does not settle becomes a question, with those calls.
   This is the demo's case: changing an existing appointment.
2. **A new agent version.** When Connexity adopts the spec for the new version, the
   assistant compares the prompts. Two things become questions: what the change leaves
   unsettled, and what contradicts an earlier answer (replacing that rule). These may
   have no calls yet.
3. **Working on an issue or a call.** While investigating, the assistant sees behaviour
   the spec does not cover and raises it, with the calls.

So calls are optional (0 to 50). Part 1 only allows an empty list.

## How the assistant knows (part 2)

The assistant knows only what Connexity tells it through MCP, and it runs only when the
person opens a session. Part 2 tells it in four places, from weakest to strongest:

1. **The tool list.** `raise_clarifications` and its description: "When calls show
   behaviour the agent's spec does not settle, raise it as a multiple-choice question
   for the person; never write it as a rule."
2. **The server instructions**, read on every connect, gain one line: "A behaviour the
   spec does not settle is a question for the person: raise it, never decide it."
3. **The spec guide.** Its "Raise these as clarifications" section becomes how to raise
   one. `get_spec` and `get_readiness` already point at the guide.
4. **Next steps at each trigger**, which the assistant follows:
   - `write_spec`: look at the agent's recent calls for behaviour these rules do not
     settle, and raise each as a clarification (trigger 1);
   - `get_spec` and `get_agent` on an adopted spec: compare the prompts, raise what the
     change leaves unsettled, and replace any answered rule it contradicts (trigger 2);
   - `get_issue`: if the spec does not say whether this behaviour is allowed, raise a
     clarification with these calls (trigger 3);
   - `get_readiness`: "7 questions wait for the person on 2 agents", then confirm the
     answers with the person.

## Done when

The service functions are tested against the local test database:

- Raising stores valid questions, and refuses each case under "Raise", storing nothing.
- Answering two questions on one agent together makes one spec version. It has the
  previous rules plus two `clarification` rules with their ids, origin `answered`, and
  who answered.
- A replacing answer drops the old rule and keeps its key.
- A second answer is refused.
- Parking makes no version, and a parked question can be answered.
- Every answer and every park writes a decision record.
- `write_spec` carries clarification rules into its version and refuses one passed in.
  Adoption copies them.
- Open counts per agent and per workspace are right, and stay inside one workspace.
- `make check` passes, including the schema drift test.

## Out of scope

- The MCP tools and the spec guide (part 2).
- The Action items page, its sidebar count and answering in the app (part 3, after the
  demo).
- The batch confirm flow (after the demo, per the roadmap row).
- Connexity raising clarifications from calls (later).
- Criticality, ranking and "N more" (parked).
- The Spec tab, "Carried over" and "In conflict" on screen (Order 16.5).

## Risks

- **Changing `write_spec` changes part 2's behaviour of #200.** A reviewer should check
  that a rewrite can never drop a clarification rule, and that its answer says how many
  it carried.
- **Near-duplicate questions.** Only identical text is caught. Part 2's guide asks the
  assistant to list open questions first.
- **A JSON list of call ids is not a foreign key.** A deleted call stays listed.

## Outcome

### Deviations from the plan

- **`spec.written_for` (new column).** Without it, answering a question on an adopted
  spec would have made a version with origin `answered`, and the spec would have read
  as current although the new prompt was never reviewed. Each version now records the
  agent version its prompt rules were last written for. A written version sets it;
  adopted and answered versions keep their predecessor's. `spec_state` is "needs review"
  when it differs from the agent's current version. The migration fills it in for
  existing specs (none on the hosted database). One behaviour changes from #200: an
  agent that returns to the version its rules were written for (7, then 8, then 7 again,
  with no spec written for 8) now reads as current, not needs review.
- **A replaced rule the spec has dropped since** is not replaced: the answer's rule is
  added with a new key, so a key the assistant dropped never comes back on another rule
  (found in review).
- **Answers are read case-insensitively** ("B" is b), found in review.
- **`write_spec`'s answer gains `changes.carried`,** the number of answered rules carried
  over. It shows in the generated client.

### Check results

`make check`:

| Gate | Result |
|---|---|
| Plan present and complete | ok |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

There is no API in this part, so the play-through is the service tests on the local test
database, plus the migration on the local `app` database:

| Step | Expected | Came back |
|---|---|---|
| `alembic downgrade 0020_spec`, then `upgrade head` | Both run | Both ran |
| `alembic check` | No drift | "No new upgrade operations detected" |
| Backfill: three throwaway specs (written for 7, adopted 8, adopted 9), then upgrade | `written_for` 7, 7, 7 | 7, 7, 7; the rows were deleted afterwards |
| Hosted database, read-only: specs by origin | Counts only | No specs, so the backfill changes nothing there |

`app/tests/services/test_clarifications.py` (15 tests) covers:
- raising, with its calls and with none;
- the spec needed first;
- every refusal, listed together with nothing stored;
- the same question asked twice;
- one spec version per agent from answers, with who answered;
- an answer being final;
- replacing a rule (and a rule dropped since);
- one question per replaced rule;
- parking and answering a parked question;
- decision records;
- answering's refusals and another workspace;
- `write_spec` carrying answered rules and refusing them;
- an answer on an adopted spec still needing review;
- open counts per workspace.

### Not done

- MCP tools, the spec guide and next steps: part 2.
- The Action items page: part 3, after the demo.
