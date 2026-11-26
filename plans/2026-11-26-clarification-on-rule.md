# A clarification is attached to its rule, and checks read both

- **Owner:** Dmytro
- **Slice:** Roadmap 105.12, "A clarification is attached to its rule, and checks read
  both"
- **Design:** The Spec tab shows each rule's clarifications under it; a question card on
  Work names the rule it explains. Prompt `designs/24-clarification-on-rule.md`;
  approved by Dmytro 2026-11-26 (Claude Design export "Connexity design review (24)",
  whose `Connexity Agent Profile.dc.html` and `Connexity Work.dc.html` replace those in
  `designs/screens/`).
- **MCP:** `raise_clarifications` (a question names the rule it explains; each answer
  carries the clarification it adds), `list_clarifications`, `answer_clarifications`,
  `get_spec` (each rule lists its clarifications) and `write_spec` (clarifications carry
  by rule key). The spec guide is rewritten where it says "the answer becomes the rule".
  Each tool's entry in `contract.py` and every input description are updated.

## Goal

A person's clarification is stored, in their own words, as its own entry tied to the
spec rule it explains, and every check that judges a rule reads the rule together with
its clarifications. A rule itself changes only when the prompt changes.

Why (Dmytro, 2026-11-26, after the spec-judging lab test):

- Decided: a spec rule is based on the prompt. The only way to change a rule is to change
  the prompt; anything else lets the spec drift.
- Decided: a clarification is a separate entry, not a rewrite of the rule.
- In the lab, one sentence of clarification per rule removed all 11 flags known to be
  wrong.
- Today an answer becomes a separate new rule. A check that judges each rule alone never
  sees it next to the rule it explains.

What is stored today (hosted database, counts only):

- 5 answered clarifications on 2 agents. None was answered "something else", and none
  replaced a rule.
- Each became a new rule. 4 of the 5 are marked critical, and test runs have judged them
  42 times.
- 4 of the 8 spec versions were made by answers (origin `answered`).

## Changes

**A clarification belongs to one rule.**

- A question names the rule it explains (`rule_key`). Each of its two to four answers
  carries the clarification it adds: one plain sentence, written when the question is
  raised, as today. "Something else" stores the person's own words.
- Once answered, the clarification is the question, the chosen answer and its sentence,
  who answered and when. It is attached to the rule's key.
- A rule can have several clarifications. A later question on the same rule may replace
  an earlier clarification (`replaces`, the earlier clarification's id). The earlier one
  stays in the history.
- Answering no longer writes a spec version (decision 3). The spec's versions come only
  from the prompt and from critical marks.

**Rules carry their clarifications across spec versions.**

- When `write_spec` writes a new version, every clarification stays with its rule's key.
- If the new version drops that key, the clarification stops applying and stays in the
  history.
- If the key stays but its text changed, the clarification carries over, and
  `write_spec`'s answer lists it under "check these still fit". The assistant raises a
  replacing question when one no longer fits.

**A gap in the prompt is its own kind.**

- The person is still asked about behaviour no rule covers: the assistant never decides
  it alone. The question is raised without `rule_key`, and its answers carry the
  sentence the prompt would need.
- The answer is stored as the person's decision, a **prompt gap**, so the same question
  is not asked again. It is not a rule, and no check reads it.
- A Work task asks the assistant to propose that prompt change to the person. Connexity
  never edits the prompt.
- When the assistant writes the spec from a prompt that covers the gap, it names the gap
  on the rule (`write_spec`, `closes`). The gap then closes and points at its rule.
- The product calls the two things by different names: a clarification explains a
  rule; a prompt gap is behaviour the prompt does not cover yet.

**Checks read both.**

- Today the only check that judges spec rules is the judge of simulated calls
  (`services/rule_judge.py`). Each rule it judges is given with its clarifications in
  force when the run started: "Rule: …", then "Clarified: …" for each one.
- The spec check (105.15) will read them the same way, through one function that returns
  a rule with its clarifications.
- Every test verdict records which clarifications were in force (their ids), so it can
  be explained and repeated later.
- That function also gives a fingerprint of the rule with its clarifications. Any stored
  model answer for a call and rule (105.15) must key on it, so a new clarification
  makes the stored answer stale.
- The lab's wording, for that function (Issues session, 2026-11-26): "This is a rule the
  AI voice agent must follow: {rule} Note on this rule: {clarification}". The note is
  repeated in what "not broken" means.

**What the assistant sees.**

- `get_spec`: each rule has `clarifications` (sentence, question, chosen answer, who
  answered, when).
- `raise_clarifications`: `rule_key` is required. An unknown key is refused with the
  spec's keys as the next step.
- `list_clarifications`: each question names its rule.
- The spec guide replaces "the answer becomes the rule" with how to write a
  clarification. It says to name the case the clarification covers and nothing
  next to it, because a broad sentence also moves the cases nearby (decision 6).

**What the person sees (after the design).**

- The Spec tab shows a rule's clarifications under it: the sentence, who answered and
  when.
- A question card on Work shows the rule the question is about, and each answer as the
  clarification it adds.
- The "From clarifications" count on the Spec tab becomes "Clarified rules".

**Data.**

- `clarification` gains `rule_key` and `replaces_id`. Each answer's stored `rule` is
  renamed `clarification`.
- The rule columns that came from a clarification (`spec_rule.clarification_id`, source
  `clarification`) go once the 5 existing rules are dealt with (decision 2).

## Decisions

1. **Behaviour no rule covers is a prompt gap, not a clarification.** Decided, Dmytro
   2026-11-26 (chose "Prompt gap", after the Issues session's view). The person still
   answers; the answer is stored and leads to a prompt change the assistant proposes.
   Once the prompt carries it, the spec is written from the new prompt and the rule
   exists. Accepted cost: until then nothing checks that behaviour, even a critical one.
   His earlier words: "only way to change spec rule is to change the prompt - otherwise
   there will be drift. Clarification as separate entry is fine."
2. **The 5 existing rules from clarifications stay until the prompt covers them.**
   Decided, Dmytro 2026-11-26 (chose "Keep until prompt has them"). Each becomes a
   prompt gap pointing at its rule, with a Work task for the prompt change. When a spec
   written from the new prompt closes the gap, the old rule goes. Nothing can create a
   new rule of this kind, and the `clarification` rule source is deleted once no agent's
   latest spec has one.
3. **Answering no longer makes a spec version.** Decided, Dmytro 2026-11-26 (chose "Own
   entry, no version"). A clarification is its own entry with the time it was answered.
   A test run reads the clarifications in force when it started and records their ids
   on each verdict.
4. **A question card stays multiple choice,** with the sentence each answer adds shown,
   and "Something else" in the person's own words. Proposed: the same as today, so the
   person sees exactly what each choice writes.
5. **Clarifications carry by rule key.** When a rule's text changes they carry over and
   are listed for the assistant to check; when its key is dropped they stop applying.
   Proposed.
6. **No measurement of a clarification's effect in this change.** Proposed. Measuring
   it is the spec check's work (105.15). The guide asks for a clarification that names
   both sides of the boundary: what counts and what does not.
   - From the lab (Issues session): a note naming both sides took the wrong flags from
     about 0.83 to 0.09 and kept the correct one at 0.88.
   - A note naming only what does not count ("a voicemail greeting is not an automated
     call screener") removed 3 wrong flags, but pulled real ones down from 0.83 to 0.70,
     and one real break scored 0.43.
   - Not tested: several clarifications on one rule, and a clarification that widens a
     rule.
7. **Earlier findings on a rule are not judged again when it gains a clarification.**
   Open, not for this change: the roadmap row "The assistant resolves a doubtful finding
   with the person" holds it. No spec check exists yet, so nothing goes stale here.

## Done when

- A question raised on rule `k` and answered adds a clarification to `k`. `get_spec`
  shows it under `k`. No new rule and no new spec version appear.
- A question without `rule_key`, or with a key the spec does not have, is refused with
  the spec's keys.
- A new spec version that keeps `k` keeps its clarifications. One that changes `k`'s
  text lists them in `write_spec`'s answer. One that drops `k` leaves them in the
  history, not applied.
- A test run's judge is given each rule with the clarifications in force when the run
  started; a clarification answered during the run does not change it.
- A later question with `replaces` set replaces the earlier clarification; the earlier
  one is in the history.
- A question without `rule_key` is a prompt gap. Answering it adds no rule and no
  spec version, puts a Work task on the agent for the prompt change, and is not asked
  again. A later `write_spec` that names it in `closes` closes it, pointing at the rule.
- The 5 existing rules stay in the spec, each with a prompt gap pointing at it. A spec
  written with `closes` for that gap drops the old rule. Checked on the local database
  with invented data, and by a migration test.
- Every test verdict records the ids of the clarifications in force.
- The contract entries and input descriptions for the five tools are updated, and the
  contract tests pass.
- The Spec tab and the question cards match the approved design.

## Out of scope

- The spec check (105.15) and the check type and inputs per rule (105.14).
- Changing the prompt. Connexity never edits it; the assistant proposes it to the
  person.
- Rule provenance and where a rule is enforced (roadmap row 135).

## Risks

- Every question about behaviour the prompt doesn't settle now ends in a prompt change.
  That is more work than picking an answer, and until it happens the behaviour is not
  checked (decision 1's accepted cost).
- Clarifications carried across a changed rule can stop fitting it. Listing them in
  `write_spec`'s answer relies on the assistant reading the list.
- 42 test verdicts reference the 5 existing rules' keys. When a spec from the new prompt
  replaces one of them, its earlier verdicts stay on the old key.

## Outcome

### Deviations from the plan

- **A prompt gap names its topic** (`gap_topic`, a few words). The approved design titles
  the assistant's task "Propose the prompt change: changing appointments", and nothing
  else held a short name.
- **A rule that closes a gap left by an earlier answer takes that rule's key and
  critical mark.** The plan expected the 42 earlier test verdicts to stay on the old key.
  Reusing the key keeps them linked, and so do the scenarios that list the rule.
- **The "Propose the prompt change" task stays with the session that took it** until a
  spec closes the gap, like an issue fix. Otherwise every `get_next_task` would hand the
  same task straight back.
- **A new task kind, `prompt_gap`,** shown on Work with the Spec type and icon, as the
  design shows it.
- **`answer_spec_id` is kept, not deleted.** It records the version each of the 5
  earlier answers made; nothing writes it any more. The plan did not list it for
  deletion.
- **A clarification on a rule takes the rule's category and `touches`;** the question's
  own are only for a prompt gap.
- **`get_spec` gives each rule from an earlier answer its `prompt_gap_id`,** so the
  assistant has the id to pass in `closes`.
- **The cards keep showing the earlier answer on a replacing question**
  (`replaces_sentence`), as decided for question cards on 2026-11-16.
- **Work's done list** counts answered questions per agent and person, because answers
  no longer make spec versions. Its wording, "N answers added to the <agent> spec", is
  unchanged: it is in the design, but a prompt gap adds nothing to the spec yet
  (`/code-review` nit, left for a design pass).
- **The decision log** also gains 105.11's row, which its pull request left out.
- **Tests rewritten, not weakened.** The tests asserting that an answer becomes a rule
  or a spec version were replaced with tests of the new model. That behaviour was
  removed on purpose (decision 1 and 3). No assertion of behaviour that still exists was
  loosened.

### Check results

`make check`, once, after this Outcome was written:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Start local database | ok | 1s |
| Backend lint and format | ok | 1s |
| Backend types (pyright) | ok | 17s |
| Backend tests and coverage | ok | 623s |
| MCP server tests | ok | 8s |
| Frontend lint | ok | 10s |
| Frontend types | ok | 10s |
| Generated client is fresh | ok | 12s |

The backend step is slow because this branch does not yet have the cheap test password
hashing of `plans/2026-11-26-fast-test-hashing.md`.

No separate play-through server: the route tests send the same requests through the
API (`TestClient` on the local database). They cover:
- raising both kinds through MCP, and the refusals;
- answering, and `get_spec` showing a clarification under its rule;
- a prompt gap answered, its Work task, and its counts;
- `write_spec` with `closes` taking the key and mark of a rule from an earlier answer;
- `check_clarifications` for a changed rule, and a dropped key;
- the question cards answered on the web;
- a test run whose judge reads the clarification and whose verdicts record it;
- the migration's columns, checked by the schema test.

**For Dmytro to check on screen:**

1. **An agent's Spec tab:**
   - tiles Rules, From the prompt, Clarified rules, Prompt gaps (muted, with the tooltip
     "Answers waiting for a prompt change"), In conflict, Open clarifications;
   - a rule with clarifications shows "Clarified: …" lines under it, each with
     "answered by <name> on <Mon d>";
   - past three, "N more clarifications" opens the rest;
   - a rule from an earlier answer reads "From an answer, until the prompt covers it ·
     answered by … on …".
2. **Work, an agent with open questions:**
   - a card about a rule shows "About the rule" and the rule quoted above the question;
   - a prompt-gap card shows "The prompt doesn't cover this";
   - every answer shows "Adds: …" or "Prompt would say: …" under its label;
   - "Something else" asks for the clarification, or what the agent should do, in the
     person's own words.
3. **Work after answering a prompt gap:** a task "Propose the prompt change: <topic>"
   with the Spec type.

### Not done

- **Not run against the hosted database.** On deploy, migration `0056` turns its 5
  answered questions into prompt gaps, each pointing at its rule. They become 5 "Propose
  the prompt change" tasks, titled by the question, since they have no topic.
- **Earlier findings are not judged again** after a rule gains a clarification
  (decision 7). Nothing produces such findings yet.
