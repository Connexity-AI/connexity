# Spec check: every call judged against the agent's spec

- **Owner:** Dmytro
- **Slice:** Roadmap 105.15, "Spec check: every call judged against the agent's spec".
  It builds on 105.11 (a call must qualify), 105.12 (clarifications on their rule) and
  105.14 (each rule's check type and inputs).
- **Design:** `designs/25-spec-findings.md`. It covers how a spec finding reads on the
  call screen and the issue page: no moment in the call and no reason, found by the
  classifier.
- **MCP:** `get_call` and `get_issue` answer a spec finding's rule, probability and
  model. A spec issue's next steps say what to do when a flag looks wrong. The
  contract entries and the issue-types doc are updated.

## Goal

Every real call that qualifies is judged against its agent's spec. The classifier
answers one yes or no question per rule: "did the agent break this rule in this call?"
A rule broken above the bar becomes a finding. All findings for one rule on one agent
make one issue, the Issue library's "Spec rule broken".

Each rule is read through `services/rule_context.py`, with its clarifications in force.
Rules that name no input are asked about the call alone. Only short inputs go to the
classifier.

Why now (the 2026-11-26 lab, one agent, 50 calls):

- At a bar of 0.9, none of the 14 flags was clearly wrong.
- Of the 12 rule breaks code could prove, the classifier found 10 at 0.8 and all 12 at
  0.7.
- Clarifications removed all 11 flags known to be wrong.
- Giving each rule only its own inputs fixed the first-call rule and two of the three
  "invented number" flags.
- Cost: $0.18 to $0.31 per 1,000 observed minutes, about 1% of the price.

On the second agent, with no clarifications yet, 0.8 still gave wrong flags on two
rules. One is "before booking, collect …", flagged on calls with no booking. Each
needs a clarification.

What the hosted database holds (counts only):

- Two agents have a spec, with 60 and 43 rules. Of those, 13 and 10 are critical.
- Last 30 days: 436 and 78 calls that qualify, 339 and 134 minutes.
- About 34 calls a day across all agents.
- Judging every qualifying call of the last 30 days on both agents again costs about
  $0.15 at the lab's rate.

## Changes

**The check.** It is a new model check, `spec_rule_broken`, a classifier (Jev),
registered beside the others.

- It runs on a call when all of these hold:
  - the call is real;
  - the call qualifies (`is_graded`, 105.11);
  - the agent has a spec.
- It is skipped on a short call or one without a spec. A skipped call is recorded as
  skipped, never as a pass.
- Which spec judges a call (Proposed): the newest spec written for, or adopted by, the
  agent version the call ran. A call on a version no spec covers is skipped: that
  agent was never given those rules. A new agent version adopts the previous spec, so
  new calls are covered.
- **What it asks:** for each rule, one yes or no question built from the rule's text
  and its clarifications in force. This is the lab's wording, with each clarification
  as "Note on this rule: …".
- **Two requests a call (decision 4):**
  - the rules that name no input, with the call alone;
  - the rules that name inputs, with the union of their short inputs.
  An agent whose rules name no input needs one request. The call is sent as numbered
  lines.
- **Which calls (decisions 3 and 5):**
  - Each call stored from release on is judged once, when it is checked.
  - Writing an agent's first spec judges its calls of the last 30 days once,
    retroactive.
  - Nothing else judges a call again.
- **Which rules it asks about:**
  - `classifier` rules: asked, and a "yes" above the bar is a finding.
  - `classifier_then_llm` rules: asked and stored, with no finding until 105.16
    confirms one (decision 2).
  - `llm` rules: not asked. 105.16 judges them.
- **Stored answer:** one per call, holding each rule's key, fingerprint and probability.
  The fingerprint is the 105.14 one. Every probability is kept, also those under the
  bar. So moving the bar later needs no new model request; it is a new check version
  that reads the stored answers again.
- **When a rule changes:** a call already judged keeps its answer (decision 3). The
  stored fingerprint records which wording of each rule a call was judged by. Calls
  judged after the change use the new wording. Judging old calls again is a later,
  explicit action.
- **Budget:** it runs within the product's daily model budget
  (`MODEL_CHECKS_DAILY_BUDGET_USD`), like the other model checks. A call it has not
  reached yet stays pending.

**The finding.**

- It names its rule (the key), the rule's text when judged, the probability and the
  model.
- **No moment and no reason.** The classifier gives neither (Decided, Dmytro
  2026-11-26: "fine for now, we give reasoning only when we can"). The finding points at
  the call as a whole, not at an event. Every finding until now points at events, so
  this is the first one with none. The call screen, the issue page and the MCP answers
  say "no moment in the call" rather than invent one.
- `found_by` is `classifier`, and the detail names the model (rule or model: the
  classifier is a model).

**The issue.**

- One issue per agent and spec rule: the key is the rule key. Rule keys carry across
  spec versions, so the issue does too.
- Its title is the rule's text. Its category is the rule's category, not one fixed
  category for the check.
- A rule removed from the spec keeps its issue (issues live forever) but gets no new
  findings.
- **Severity (Proposed, from the Issue library's "Set per rule"):** a broken critical
  rule fails the call, and any other rule only flags. The agent's setting for the
  check still applies:
  - Off: the check does not run.
  - Flags: every rule only flags.
  - Fails the call: the default, critical rules fail the call.

**MCP.**

- `get_call` and `get_issue` answer a spec finding's rule key, rule text, probability
  and model, and say that it has no moment in the call.
- A spec issue's next steps, numbered:
  1. Read the rule and its clarifications (`get_spec`).
  2. If the flag looks wrong because the rule is unclear, raise a clarification on that
     rule (`raise_clarifications` with its `rule_key`).
  3. If the rule's check type or inputs are wrong, fix them with `write_spec`.
  4. If the agent broke the rule, fix the agent as for any issue.
- `get_spec` keeps what 105.14 gave it, and says how many rules are not asked by this
  check yet (`llm`), and how many it judges with their flags held for 105.16
  (`classifier_then_llm`).
- Contract entries for `get_call` and `get_issue` are updated, along with the spec
  guide's section on check types (what each type means now that the check runs).

**Screens (from the design).**

- The call screen lists a spec finding with the other findings. It shows the rule, "no
  moment in the call", and the classifier as what found it.
- The issue page of a spec issue shows the rule as its title, with its clarifications.
- Nothing else on screen changes.

**Docs.**

- `docs-internal/checks-and-incidents.md`: the spec check, what it is given, the bar,
  and findings with no moment.
- `docs-internal/issue-types.md`: the "Spec rule broken" row; a test fails without it.
- The decision log.
- The Notion "Check costs" table: the production cost once measured.

## Decisions

1. **The bar is 0.8.** Decided, Dmytro 2026-11-26 (chose "0.8"). A "yes" at 0.8 or above
   is a finding. Wrong flags on unclear rules are fixed with clarifications.
2. **`classifier_then_llm` rules are asked and held hidden until 105.16.** Decided,
   Dmytro 2026-11-26 (chose "Asked, held hidden"). The classifier judges them and the
   answer is stored, but no finding is raised until the LLM step confirms it. So no
   unverified flag on a conditional rule is shown.
3. **New calls only.** Decided, Dmytro 2026-11-26: "New calls only. In future we will
   have a way to rejudge - but explicitely only". A call is judged once, against the
   spec in force when it is judged, and keeps that answer when a rule changes later.
   Judging old calls again will be an explicit action of its own, not part of this
   change.
4. **Two classifier requests per call.** Decided, Dmytro 2026-11-26 (chose "Two
   requests", after the Issues session measured it). One request asks every rule that
   names no input, with the call alone. The other asks every rule that names inputs,
   with the union of their short inputs. On the first agent's 50 lab calls it cost
   $0.21 per 1,000 observed minutes, against $0.31 for one request per input set. It
   moved no more of the 55 other rules' answers than the classifier's own noise (12 of
   2,750 by more than 0.1, against 10 for one per set and 98 for every input to every
   rule). The first-call and "invented number" fixes held. Not tested: many input rules
   sharing a large union.
5. **An agent's first spec judges its last 30 days once.** Decided, Dmytro 2026-11-26
   (chose "First spec, 30 days"). When an agent's first spec is written, its
   qualifying calls of the last 30 days are judged once. Only calls on an agent version
   that spec covers count. This is the onboarding audit. Those findings are marked
   retroactive and count for nothing in the score. Releasing the check judges no
   stored call: the two agents with a spec today start with new calls. After that,
   decision 3 holds.

Proposed, not asked:

- **Rules that depend on facts written in the prompt,** such as approved claims, cannot
  be judged by the classifier, which never sees the prompt. The guide tells the
  assistant to type them `llm`, so the classifier does not judge them and 105.16 can
  give the LLM the prompt.
- **Severity** as above.
- **Which spec judges a call** as above.

## Done when

- A qualifying real call of an agent with a spec gets a `spec_rule_broken` run. Each
  `classifier` and `classifier_then_llm` rule is asked once, with its clarifications.
  Rules with no inputs go in one request with the call alone. Rules with inputs go in
  a second request with the union of their short inputs.
- Releasing the check judges no stored call. Writing an agent's first spec judges its
  qualifying calls of the last 30 days on a covered version once, with retroactive
  findings that count for nothing in the score.
- A rule above the bar gives a finding with no event, its rule key, text, probability
  and model. All findings for one rule make one issue, titled by the rule, in the rule's
  category.
- A critical rule's finding fails the call; any other rule's finding flags it. With
  the agent's setting at Off, the check does not run; at Flags, nothing fails.
- A short call, or a call of an agent with no spec, is recorded as skipped.
- Changing a rule's text, a clarification, its check type or its inputs leaves calls
  already judged as they were. The next call is judged by the new wording, and the
  stored fingerprint shows which wording judged each call.
- A `classifier_then_llm` rule's answer is stored and raises no finding.
- The daily model budget stops it like the other model checks.
- `get_call` and `get_issue` answer as above, the next steps are numbered, the contract
  entries and input descriptions are updated, and the contract tests pass.
- The call screen and the issue page show spec findings as the design does.
- Tests on invented calls cover each of these, with Jev mocked (`respx`) for timeout,
  empty and malformed answers.

## Out of scope

- The LLM approval step and `llm` rules (105.16).
- Marking a finding a false positive, and the assistant resolving a doubtful one with
  the person (105.17).
- Rules that depend on the call history (parked, Dmytro 2026-11-26).
- A hidden release. The check is public on release, like every check so far; check
  stages are their own future row.
- Simulated calls. Test runs keep their own judge.

## Risks

- **Wrong flags on rules not yet clarified.** The second agent's lab run had two such
  rules at 0.8. Until the assistant adds clarifications, those issues hold wrong
  findings. The next steps point straight at the fix.
- **Rules still on the default `classifier`.** A conditional rule the assistant has not
  retyped is judged by the classifier alone.
- **Tested on two agents, one platform.** The critical booking rules were not tested for
  misses on the first agent, and that agent's set had two bookings.
- **A first-spec backfill shares the $1 daily model budget.** A large workspace's 30
  days could take several days to judge, newest calls first. On today's volume it is
  cents.
- **A finding with no event is new.** Every place that reads a finding's moment has to
  handle none: the call screen's order, the incident timeline later on, and the MCP
  answers. Tests cover each reader that exists today.

## Outcome

### Deviations from the plan

- **The check shape grew three parts,** so a check can read the database without
  breaking the engine's pure `run`:
  - `Check.applies`: whether a call is judged, given the check's release;
  - `ModelCheck.prepare`: what `ask` needs beyond the trace, here the rules and inputs;
  - `Check.whole_call`: findings that point at no event.
  The classifier check that already existed takes the new `ask` argument and ignores
  it.
- **Issues are named after their rule** through a new column, `issue.subject`
  (migration `0058`). It holds the rule's text as its newest finding judged it.
- **The spec-in-force rule moved to the data layer** (`crud.spec_covering`, with
  `version_number`), so the check can use it without an import cycle. `spec_in_force`
  answers as before.
- **No skip for "no rule to ask"** (from `/code-review`). A call whose spec has no
  classifier rule is judged with an empty answer, which costs nothing. Without that,
  retyping every rule `llm` would have erased the findings of calls already judged.
- **The two requests go out in parallel** (from `/code-review`).
- **`get_spec` counts** `held_for_llm` and `llm_only`.
- **The settings description** says that only a critical rule fails the call.
- **Screens:** the export of 2026-11-26 (`Connexity design review (25)`), from which
  only the Call, Issue and Issues pages are taken. The same export carried changes to
  Settings and the overview canvas from other work; they are not in this pull request.
- **External calls:** the Jev client's own tests cover timeout, empty and malformed
  answers (`test_jev.py`). The spec check's tests fake Jev and cover a failed request,
  which leaves the call pending with no finding.

### Check results

`make check`, once, after this Outcome was written:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Start local database | ok | 1s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 12s |
| Backend tests and coverage | 1 failed, 1,241 passed | 123s |
| MCP server tests | ok | 4s |
| Frontend lint | ok | 2s |
| Frontend types | ok | 1s |
| Generated client is fresh | ok | 8s |

The one failure was `test_spec_tab.py`, which lists every spec count exactly and lacked
the two new ones (`held_for_llm`, `llm_only`). Fixed, and that file passes. The full run
was not repeated.

No separate play-through server: the tests run the scheduled pass (check, then ask the
faked model) on the local database with invented agents and calls. They cover:
- the bar, and held `classifier_then_llm` rules;
- the first-spec backfill, marked retroactive, and judging once;
- critical against flags, and the Flags and Off settings;
- the two requests with the union of short inputs, with `llm` rules not asked;
- clarifications in the question;
- each skip: short call, uncovered version, test call, no spec, before the release;
- a failed request;
- the call screen, the issue page and the MCP answers;
- retyping every rule keeping the findings of calls already judged.

**What Dmytro should open:**
- **A call with a spec finding:** the finding reads as the rule, with "Spec rule broken
  · no moment in the call · found by the classifier, 0.9x". It has no mark on the
  timeline and its time shows "—". Clicking it opens the issue.
- **That issue:**
  - the rule is the title, with "Spec rule broken · <category>" and its clarifications
    under it;
  - the classifier note sits under the tiles;
  - Affected calls has a Probability column.
- **Issues:** the row shows "Spec rule broken" under the rule's text.

On hosted data the two agents with a spec start with new calls only, so a spec finding
appears once a new call breaks a rule.

### Not done

- **Measuring the long inputs once per pass** (from `/code-review`, skipped). Each call
  prepared measures the agent's inputs again. At today's volume that is a few calls a
  minute.
- **The Notion "Check costs" row** gets its production cost once real calls are judged.
- **105.16 (the LLM step) and 105.17 (false positives).**
