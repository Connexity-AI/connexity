# False positives: the assistant resolves a doubtful finding with the person

- **Owner:** Dmytro
- **Slice:** Roadmap 105.17, "The assistant resolves a doubtful finding with the
  person". It builds on 105.12 (a clarification on its rule), 105.15 (the spec check)
  and 105.16 (the LLM step, whose dismissed flags this shows).
- **Design:** `designs/27-not-counted.md`, the prompt from the roadmap row with the two
  fixes Dmytro ran on 2026-11-27 (a loading line; dismissed flags at 0.80 or above).
  Export "Connexity design review (28)": only the Issue screen is taken.
- **MCP:**
  - two new tools, to mark findings as false positives and to undo that;
  - `get_issue` gains the two counts and, when asked, the paginated "Not counted"
    list;
  - `list_calls` with an `issue_id` gives each finding's id, so the assistant can name
    the findings it marks;
  - the issue's rules and next steps name the path, and the spec guide has a step
    for it;
  - contract entries and input descriptions for every tool that changes.

## Goal

When a finding looks wrong because its spec rule is unclear, the assistant follows one
path (Dmytro: "1. Confirm with user 2. Create spec rule clarification 3. decide if keep
issue and work on it or mark as false positive"):

1. It doubts the issue's findings and reads the calls.
2. It asks the person what the rule means.
3. It records the answer as a clarification on the rule (exists since 105.12). New
   calls are judged with it.
4. It marks the old wrong findings as false positives, naming that clarification. This
   step is new.
5. It works on the findings that are left.

Old calls are never judged again (Decided, 2026-11-26), so without step 4 the wrong
findings stay forever. On the second lab agent, one clarification fixed eight of nine
wrong flags on new calls, and nothing could clear the old ones.

## Changes

**The mark, on the finding.**

- A finding gains a false-positive mark. It records:
  - when it was marked;
  - who marked it: a person, or the assistant by its name;
  - the reason;
  - the clarification it rests on, if any;
  - who approved it, when approval was needed.
- The mark lives on the finding's row. Checking the call again keeps the row, and so
  the mark, while the check raises the same finding. One migration adds the columns.
- **A marked finding counts nowhere** (Decided, 2026-11-25): not on its call, not in
  any score, the call result, the dashboard, Work, the calls list or the issue's size
  and chart. It stays stored. This is one filter beside the archived-issue one
  (`shown_finding`), also used by the issue list and the issue page, which read
  findings of archived issues too.
- **Undo** removes the mark. The finding shows and counts again.
- **Recorded:** every marking and undo is a decision on the issue, one per batch, with
  who, the reason and how many findings. It shows in the issue's history ("8 findings
  marked as false positives · Claude Code, approved by Alex"), as in the design.
- **Nothing changes for future calls** (Decided, 2026-11-27). A marking suppresses
  nothing new. The future is changed only by a clarification, the check's setting or
  archive.

**Who may mark without asking** (Decided, 2026-11-27, agreed as proposed):

- The assistant marks without asking again when a clarification the person answered
  covers the findings. It names that clarification, and the clarification must be on
  the issue's own rule.
- Otherwise the person approves first: no clarification behind the marking, any check
  without a spec rule, or a critical spec rule. The person approves in the conversation
  with the assistant (Decided, 2026-11-27); Connexity shows nothing waiting.
- Any finding from any check can be marked (Decided, 2026-11-27: "Any finding, lets not
  complicate").
- When approval is needed and the call does not name who approved, the tool refuses
  and says why (decision 1).

**Dismissed flags (105.16).**

- A flag the LLM step dismissed is read from the stored answer. It never became a
  finding.
- "Bring back" records on that answer who brought it back and when. The call is
  checked again, and the flag becomes a finding. The check stays pure: it reads the
  answer.
- A brought-back finding can then be marked like any other.
- A dismissed flag shows only on its rule's issue, so a rule with no issue yet shows
  its dismissed flags nowhere.

**The counts and the list** (Decided, 2026-11-27: "Not Counted as collapsed by
default").

- The issue page's answer carries only two counts: findings marked as false
  positives, and flags dismissed by the model.
- The rows come from a separate, paginated request made when the list is opened:
  - marked rows: the call, its moment, who, when, the reason, the clarification and
    the approver;
  - dismissed rows: the call, its moment, the model, the classifier's probability and
    the model's reason.
  - Newest first.
- The same two counts per check are in `get_issue`'s check section, for the agent. They
  are numbers only: nothing is suppressed because of them.

**MCP** (decision 2).

- `mark_false_positives`:
  - takes the issue, a list of its finding ids (up to 200), the reason, the
    clarification if any, and who approved when approval is needed;
  - checks that every finding belongs to the issue, and that the clarification is
    answered and on this rule;
  - answers how many were marked, the new counts and the next steps.
- `undo_mark_false_positives`:
  - takes the issue and a list of marked finding ids to undo, and dismissed flags to
    bring back (by call id);
  - its answer warns that each one shows on its call and counts in the score again.
- `get_issue`:
  - the two counts;
  - with `not_counted` true (and `cursor`), the list instead of the affected calls;
  - its rules say when the assistant must ask the person first;
  - its numbered next steps name the path: doubt, ask the person, clarification,
    mark the old findings, work on what is left. If the same wrong finding keeps
    coming back, the fix is a clarification, the check's setting, or archive.
- `list_calls` with `issue_id`: each issue finding's `id`.
- The spec guide: a section "A finding that looks wrong", with the path.
- Contract entries for the two new tools, `get_issue` and `list_calls`.

**Screens (from the design).** The issue page only; the call screen does not change.

- A quiet line under the tiles: "8 findings marked as false positives · 2 flags
  dismissed by the model". Each half shows only above zero. Clicking it opens the list.
- The "Not counted" card below the affected calls is closed by default. Opening it
  fetches the rows, showing "Loading…" meanwhile.
  - Two groups, each with its heading and count.
  - Ten rows per group, then "Show all N", which fetches the rest.
  - Undo and Bring back each ask once: "This finding will show on its call again and
    count in the score."
- The calls-affected tile, the chart and the affected calls leave marked findings out.
  When nothing is left: "No calls affected now."
- History lines for markings, undos and bring-backs.

**Docs.**

- `checks-and-incidents.md`: false positives and dismissed flags;
- `issue-types.md`: marking applies to every type;
- `data-model.md`: the mark;
- the decision log.

## Decisions

From the roadmap row, worked through with Dmytro on 2026-11-27, all in force:

- **Marked on findings, many at once.** "agree false positive is marked on findings,
  many at once". Archive stays the action for a whole issue.
- **When the assistant may mark without approval:** agreed as proposed (above).
- **Any finding, from any check.** "Any finding, lets not complicate".
- **Nothing changes for future calls.** "agree nothing for now. Eventually we will find
  a true fingerprint of the issue and when we can with confidence say those findings
  are 100% this ... issue then we would auto dismiss them but not till then".
- **Approval in the conversation.** "In the conversation with the assistant".
- **Where markings are seen and undone:** agreed as proposed. The issue page has a count
  that opens the list, the call screen shows nothing, and MCP has the same list and
  undo. Flags the LLM step dismissed appear in the same list and can be brought back.
- **"Not counted", closed by default, loaded when opened.** "lets do Not Counted as
  collapsed by default to save requests as this will rarely will be opened".

Asked in this plan:

1. **A marking that needs approval and names no approver is refused.** Decided, Dmytro
   2026-11-27 (chose "Refuse and say why"). Nothing is marked. The answer says which
   findings need the person, and why: no clarification, a check with no rule, or a
   critical rule.
2. **Two tools: `mark_false_positives` and `undo_mark_false_positives`.** Decided,
   Dmytro 2026-11-27: "two tools but i dont like couint_again - maybe
   undo_mark_false_positives?". The second undoes marks and brings back dismissed
   flags. The list comes from `get_issue` with `not_counted`, not from a third tool.
3. **An issue whose findings are all marked keeps its state.** Decided, Dmytro
   2026-11-27 (chose "State unchanged"). It shows no affected calls and keeps its list;
   nothing resolves or archives it by itself.

Proposed, not asked:

- The mark is stored on the finding's row.
- A dismissed flag is brought back by recording that on the stored answer, then
  checking the call again.
- One decision record per batch, shown in the issue's history.
- The assistant names an approver as the person's name or email, as given in the
  conversation. Connexity does not check it against the workspace's people.

## Done when

- `mark_false_positives` on a spec issue's findings, with a clarification answered on
  its rule:
  - marks them without an approver;
  - with a critical rule, needs one;
  - on a code check's findings, needs one;
  - without one, refuses and names the findings and why.
- A marked finding is gone from:
  - its call screen and the call's result;
  - the score, the dashboard, Work and the calls list;
  - the issue's size, chart and affected calls.

  It is still stored, in the "Not counted" list and in `get_issue`'s count.
- Checking the call again, also under a new check version that raises the same
  finding, keeps the mark.
- `undo_mark_false_positives` undoes a mark, and the finding counts again. It brings back a
  dismissed flag, which becomes a finding. Both show in the issue's history.
- A new call that breaks the rule the same way is a finding like any other.
- With every finding marked, the issue's affected calls are empty and its state is
  unchanged.
- The issue page answer carries only the counts. The list is a separate, paginated
  request.
- `get_issue`, `list_calls` and the two new tools answer as above, and the contract
  tests pass.
- The issue page shows the line, the card, loading, Undo and Bring back as the design
  does.
- Tests on invented agents and calls cover each of these through the API.

## Out of scope

- Dismissing similar findings automatically (decision 4 of the row).
- Judging old calls again after a clarification.
- A page of false positives across the workspace.
- Marked findings greyed out on the call.
- An approval screen, or anything waiting for the person in Connexity.

## Risks

- **A new check version that changes a finding's identity loses its mark.** If a
  check's next version points the same problem at other events, the old row is
  replaced and the finding counts again. Today no check changes identity across
  versions. The tests cover the same identity.
- **Dismissed flags are read from stored answers,** a JSON query over the agent's
  calls. At today's volume this is cheap. It runs only when the list or the count is
  read.
- **The approver is the assistant's word.** Connexity records the name it is given;
  the approval itself happened in the conversation.

## Outcome

### Deviations from the plan

- **The approver is the person the assistant acts for, not a name it types.**
  - `mark_false_positives` takes `approved: true`, and the approver recorded is the
    signed-in person.
  - Approving needs someone who may approve in the workspace, as archiving does
    (`_require_approver`).
  - This replaces the proposal to record a name the assistant is told. Connexity then
    records only who it knows.
- **`get_issue`'s `not_counted` names the group** (`false_positives` or `dismissed`)
  and pages by `offset`, 10 a page, instead of a true/false switch with a cursor.
- **An issue whose findings are all marked keeps its severity,** read from all its
  findings, marked ones included, on the issue page. Found in review.
- **A brought-back flag is the classifier's finding.** It has no model reason, because
  the model's reason argued against it. It carries `brought_back_by`, and no
  `confirmed_by`.
- **Undo and Bring back in the app need no approver:** they make a finding count
  again, never less. They are recorded as the person's.
- **History lines** read, for example, "8 findings marked as false positives by Claude
  Code for Alex, 27 Nov · 'reason'".
- **`list_calls` with an issue** now leaves out marked findings and the calls that have
  only marked ones, as the issue's size does.

### Check results

| What | How | Result |
|---|---|---|
| Marking with a clarification, without asking; marked findings count nowhere (call screen, result, `list_calls` by issue, size, affected calls); the mark kept when the call is checked again; the list with the clarification | `test_a_clarification_lets_the_assistant_mark_and_marked_findings_count_nowhere` | Pass |
| Refused without approval: no clarification, a critical rule; a clarification of another rule; another issue's finding | `test_a_marking_that_needs_the_person_is_refused_without_approval` | Pass |
| A code check's finding needs the person; undo; history; an all-marked Critical issue keeps its severity and state | `test_a_code_check_finding_needs_the_person_and_can_be_undone` | Pass |
| A dismissed flag listed with its model, probability and reason; brought back as a finding; refused the second time; the check's counts | `test_a_flag_the_model_dismissed_is_listed_and_can_be_brought_back` | Pass |
| The web list a page at a time, counts only on the page, count again from the app, 404 for another issue | `test_the_web_list_loads_a_page_at_a_time_and_counts_again` | Pass |
| Spec check, issue page, issues list, MCP issues, call screen, calls, engine, dashboard, issues, Work, score, issue-types doc, schema | the touched test files | Pass |
| MCP contract and adapter, the tool list | `mcp_server` tests | Pass |
| Frontend | `pnpm lint`, `pnpm turbo check-types` | Pass |
| Every gate | `make check`, once, before the pull request | Pass |

No play-through server: the route tests send the same requests through the API.

### Review (`/code-review`)

- **Fixed, important:** the dismissed count for the check read every stored answer of
  the agent on each `get_issue`. It is now counted in the database.
- **Fixed, small:**
  - one "Loading…" line for the whole list instead of one per group;
  - an all-marked Critical issue showed as a Warning;
  - a confusing expression for who marked a finding.

### Not done

- **Dismissed flags of a rule with no issue yet are shown nowhere.** An issue exists
  only once a rule has a finding.
- **The issue list's severity** of an issue whose findings are all marked still comes
  from counted findings. Such an issue has no calls in any period, so the list shows it
  only under all-time filters.
- **Automatic dismissal of similar findings, judging old calls again, and a
  workspace-wide list of false positives** are out of scope, as planned.

### Pages for Dmytro to open

- **An issue with findings marked** (mark some through the assistant first):
  - A quiet line under the tiles, "N findings marked as false positives".
  - Clicking it opens "Not counted": "Loading…", then the rows. Each row has the call
    with its moment, "Marked by … on …", the reason, "Rests on: Clarified: …" when it
    has one, and "Approved by …" when the person had to approve.
  - Undo asks once, then the finding is back in the affected calls and the line's
    count drops.
- **A spec issue with flags the model dismissed:** "Dismissed by the model" rows with
  "Dismissed by Claude Haiku 5.5 · flagged by the classifier, 0.8x" and the model's
  reason. Bring back asks once, then the call joins the affected calls.
- **An issue with every finding marked:** "No calls affected now.", the Not counted
  card, and its severity unchanged.
- **The history** shows a line per marking, undo and bring-back.
