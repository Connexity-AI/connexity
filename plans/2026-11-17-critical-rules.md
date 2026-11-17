# Critical rules

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Critical rules" (10.12905). It comes before
  scenarios (10.1291), the text runner (10.1292) and test results (10.1293), which use
  it.
- **Design:** `docs-internal/testing.md` decisions 6 to 8 (PR #218, not merged yet; it
  wins over prompt 08). The Spec tab's design has no Critical label yet (question 5).
- **MCP:**
  - `get_spec` answers `critical` on each rule, and a critical count;
  - `write_spec` takes `critical` on each rule;
  - a new tool, `mark_critical_rules`, marks rules or clears the mark without
    rewriting the spec;
  - the spec guide says which rules are critical.

## Goal

Every spec rule is Critical or not. A critical rule is one whose failure must stop a
release: the agent made up a price, booked without the caller's details, skipped a
required disclosure. A failure of any other rule is a Warning: two questions in one
turn. The assistant marks rules as it writes the spec, without asking. The person sees
the mark on the Spec tab. Test results (10.1293) later fail a version on a failed
critical rule.

## Decided

These are Dmytro's words, from `testing.md`:
- **Critical or not, and what it means** (decision 6): "if critical rule failed - like
  agent made up pricing thats a fail. If non critical rule failed … it's a warning".
- **The assistant sets it without asking** (decision 7): "In this case this decision is
  not critical".
- **A rule from a Critical issue does not start out Critical, for now** (decision 8).

## What exists

- **Spec rules are never edited** (`models/spec.py`). Any change is a new spec version:
  - written by the assistant;
  - adopted when the agent moves to a new version;
  - answered, when answers to questions add rules.
- **A rule's `key` stays the same across versions.** That is how versions are compared
  (kept, added, dropped).
- **`write_spec` takes every rule from the prompt.** Rules from answered questions are
  carried over without being passed in.

## Changes

### Where the mark lives (question 1)

- **`spec_rule` gains `critical`,** false by default (migration `0028`). The mark
  belongs to a spec version like the rule's text, so a version's test results can
  always be read against the marks it had.
- **Carried by key into every later version:** adopted, answered and written. A rule
  that `write_spec` passes without `critical` keeps its previous mark.
- **A question that replaces a rule** (`replaces_key`) gives its new rule the replaced
  rule's mark (question 3).

### MCP

- **`write_spec`:** each rule takes `critical` (true or false, optional).
- **`mark_critical_rules(workspace_id, agent_id, critical[], not_critical[])`:**
  - takes rule keys of the agent's latest spec;
  - makes a new spec version, its origin "marked": the previous rules unchanged, with
    the new marks;
  - refuses an unknown key, or a key in both lists, and stores nothing then;
  - when nothing would change, answers so and makes no version.
- **`get_spec`:** each rule answers `critical`, and `counts` gains `critical`.
- **Next steps:**
  - `write_spec` ends with "Mark the rules whose failure must stop a release
    (`mark_critical_rules`)" when the spec has no critical rule;
  - otherwise it names how many are critical.
- **The spec guide** (`connexity://guides/spec`) gains "Critical rules" (question 2):
  - **Critical:**
    - making up facts the business owns, such as prices, availability and policies;
    - money;
    - safety, and sending emergencies to the right place;
    - legal and compliance, such as disclosures, consent and personal data;
    - actions with real effects, such as booking, cancelling and transfers.
  - **Not critical:** style, phrasing, turn length and order of small talk.
  - **When unsure, not critical.** The person can ask the assistant to change it.

### The Spec tab

- **A "Critical" label** on each critical rule, and "N critical" beside the group's name.
  It matches the issue rows' severity badge (question 5).
- **The versions list** names a "marked" version as "Critical rules marked by …".

## Decisions

- Everything under "Decided" is Decided.
- **No task on Work for marking:** it is part of writing the spec (question 4).
- Everything under "Questions" is Proposed until Dmytro answers.

## Questions

1. **The mark belongs to the spec version.** Recommend it, so a version's results are
   read against the marks it had, and the versions list shows when a mark changed. The
   cost is one more spec version each time marks change. The alternative is one mark
   per agent and rule key, outside the versions: no extra versions, but changing a mark
   rewrites how past results read.
2. **The guide's list of what is critical.** Recommend the list above, with "when
   unsure, not critical", so a version fails only for what matters. Say what to add or
   take out.
3. **A replacing answer keeps the mark.** When the person's answer replaces a critical
   rule, recommend the new rule starts out critical: it settles the same behaviour. The
   alternative is that it starts out not critical, like every new rule, and the
   assistant marks it again.
4. **No Work task.** Recommend none: `write_spec`'s next step asks the assistant to mark
   them. The alternative is a task "Mark critical rules on Front desk" per agent with no
   critical rule. That one would never leave for an agent with no rule worth marking.
5. **The Spec tab's label before the design has it** (rule 9). The Agent Profile design
   shows the Critical badge on issue rows only. Recommend that I write a short Claude
   Design adjustment prompt in `designs/12-adjustments.md` (the badge on a critical rule
   and "N critical" on its group, as on issue rows). The tab is built after you update
   the design. The alternative is backend and MCP only here, and the label later.

## Done when

- **Through the API,** in the route tests on the local database:
  - `write_spec` stores marks, and a rule passed without `critical` keeps its previous
    mark;
  - an adopted and an answered version carry the marks by key;
  - a replacing answer keeps the replaced rule's mark;
  - `mark_critical_rules` makes one "marked" version, refuses unknown keys and keys in
    both lists, and makes none when nothing changes;
  - `get_spec` answers each rule's mark and the critical count.
- **`make check` passes** once, before the pull request.
- **The design adjustment is written** for the Spec tab (question 5). The label on
  screen is built after Dmytro updates the design.

## Out of scope

- Using the mark in test results (10.1293) and the threshold for warnings (open
  question 1 in `testing.md`).
- Starting a rule out critical from a Critical issue (decision 8, "for now").
- Marking on screen: the assistant does it (decision 7), and the person asks it to.

## Risks

- **Too many rules marked critical** would fail every version. The guide's "when
  unsure, not critical" and the critical count in `get_spec` keep this visible.

## Outcome

### Deviations from the plan

- **No Spec tab change in this pull request** (question 5): the label waits for the
  design. `designs/12-adjustments.md` item 29 is the prompt: the Critical badge on a
  rule, "N critical" on its group, and the "marked" line in the versions list.
- **The web app shows no versions list yet,** so "Critical rules marked by …" comes
  with the label, not here. The regenerated client knows the `marked` origin.
- **`mark_critical_rules` returns the spec as `get_spec` does,** with the number of
  rules changed in its first next step.
- **The migration's downgrade** turns "marked" versions into "adopted": without the
  column they are unchanged copies of the version before.
- **The 422 answer of `write_spec`** is built by a helper shared with
  `mark_critical_rules`; its wording is unchanged.
- **Review findings, both fixed:**
  - the next step now reads "1 of the spec's 2 rules is critical";
  - marking reads the latest version's rules once.

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

While building, only the touched test files ran:
- `test_critical_rules.py` (new), `test_spec_api.py`, `test_spec_tab.py`,
  `test_mcp_clarifications.py`, `test_clarifications.py`, `test_work_page.py` and the
  schema conventions tests;
- the MCP server tests.

Then the full `make check` ran once (CLAUDE.local.md). No separate play-through server:
the route tests send the same requests through the API on the local database.
- **`write_spec`** stores marks. A kept rule passed without `critical` keeps its mark,
  and `critical: false` clears it.
- **An adopted version and an answered version** carry the marks by key. An answer that
  replaces a critical rule keeps its key and its mark; a new answer is not critical.
- **`mark_critical_rules`:**
  - makes one "marked" version with the rules unchanged, and the spec stays current;
  - the earlier version keeps its marks;
  - it makes no version when nothing changes;
  - it refuses unknown keys, keys in both lists, an empty call, an agent without a
    spec, and another workspace's agent.
- **`get_spec`** answers each rule's mark and the critical count. `write_spec`'s next
  steps point at `mark_critical_rules` when no rule is critical.

`test_spec_tab.py`'s exact `counts` check gains `critical: 0`; nothing was weakened.

**For Dmytro:** nothing to check on screen yet. Update the Agent Profile design from
`designs/12-adjustments.md` item 29; the Spec tab's label is built after that.

### Not done

- The Spec tab's Critical label and the versions list line (question 5), after the
  design.
- Using the marks in test results (10.1293).
