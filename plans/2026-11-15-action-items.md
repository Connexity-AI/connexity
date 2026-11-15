# Action items page for clarifications

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Action items page for clarifications"
  (10.122). It was split off from 10.12 and placed after the Spec tab (10.121), Dmytro,
  2026-11-15. This branch is cut from the Spec tab's (Connexity-AI/connexity#205) and
  is rebased onto `main` once that merges.
- **Design:** `designs/03-action-items-and-spec.md` (Action items part),
  `designs/12-adjustments.md` item 5 (one list, no tabs). Screen:
  `designs/screens/Connexity Action items.dc.html`.
- **MCP:**
  - `answer_clarifications` gains `reopen` for a parked question (question 4);
  - `list_clarifications` lists open questions most important first, as the page does
    (question 2), and gains an `answered_since` count.

## Goal

One place, across all agents, where the person sees the questions waiting for them and
answers them in the app as well as through their assistant. They see the most important
few, never hundreds at once, and what was answered and parked. The Spec tab's open count
and "In conflict" line now lead there.

## What exists

- **Clarifications** (10.12): raised, answered (a to d, final) and parked through MCP.
  Answers for one agent make one spec version, and every answer and park is a decision
  record.
- **`list_clarifications`:** newest first, filtered by agent and state, with counts.
- **The Spec tab** (10.121, #205): an Open clarifications tile and an "In conflict" line,
  neither linked yet.
- **The sidebar:** Agents, Calls and Issues, with no counts.

## Changes

### The page: `/action-items`

- **Page bar:** "Action items", with the caption "Across all agents · most important
  first". An Agent picker on the right filters it (`?agent=`), and the caption becomes
  "3 open for this agent".
- **Tiles:**
  - Open;
  - Answered this week (the last 7 days);
  - Parked.

  No Critical tile (question 1).
- **The list:** open clarifications, most important first (question 2). It shows the
  top 5, then a quiet "38 more" line that shows 5 more each time (question 6). With an
  agent picked, it shows all of that agent's.
- **A clarification card:**
  - the agent's name, linking to its page;
  - the kind: "Clarification", or "Conflict with an earlier answer" for one that
    replaces a rule;
  - the question in one sentence;
  - the evidence in one muted line, "Seen on 9 calls · spec version 3", with "Open a
    call" leading to its first call. A question with no calls says "Raised from a
    prompt change · spec version 3";
  - for a conflict, the earlier answer quoted: "Earlier answer, by Dmytro on 15 Nov:
    Change an existing appointment only when the caller asks" (question 7);
  - the answers as two to four buttons (a to d). Each button's rule shows on hover;
  - a quiet "Park".
- **Answering in the app** (question 3):
  - Picking an answer opens a short confirm in the card: "Answer b: 'Change an existing
    appointment only when the caller asks.' This becomes a rule in the spec. An answer
    is final." It has Confirm and Cancel.
  - Confirming records the person as the one who answered, with no assistant, and adds
    the rule in a new spec version.
  - The card leaves the list.
- **Answered,** collapsed below the list, with its count: agent, question, the chosen
  answer, and "Answered by Dmytro, 15 Nov". The last 7 days, newest first, then "N more
  this week".
- **Parked,** collapsed, with its count: agent, question, when it was parked, and
  "Reopen" (question 4). Newest first, with "N more".
- **Nothing open:** "Nothing needs your input", and the Answered and Parked sections
  stay.
- **Only clarifications.** The design's other kinds (archive proposals, check settings,
  versions live without passing their tests) appear when their features exist
  (rule 14).

### Links into it

- **Sidebar:** "Action items", first (the decided order is Home, Incidents, Action items
  and so on; Home and Incidents are not built), with its open count in muted text next
  to the name, as designed. No count when none are open.
- **The Spec tab:** the Open clarifications tile opens `/action-items?agent=<id>`.
  "In conflict" gains "Open the clarification", leading there too.

### The API

- **Web routes** (cookie auth; the page reads and answers through them):
  - `GET /clarifications?state=&agent_id=&cursor=`: the same list and counts as MCP,
    plus `answered_since` (answered in the last 7 days);
  - `POST /clarifications/answers`: the same service as MCP. Refusals answer 422 with
    every problem.
- **Importance order** for open questions, in both: more calls seen first, then those
  that touch money, safety or compliance, then the newest (question 2). Answered and
  parked stay newest first.
- **`reopen`:** a parked question goes back to open. An open or answered one is refused.
  It is a decision record (`clarification_reopened`).

## Decisions

- **One list with no tabs, and incidents not on it.** Decided (`12-adjustments.md` item
  5).
- **No criticality yet.** Decided (2026-11-11: "no criticality for now park it").
- **The person can answer in the app as well as through their assistant.** Decided
  (roadmap row 10.122).
- **Items other than clarifications** wait for their features (rule 14).
- Everything under "Questions" is Proposed until Dmytro answers.

## Questions

1. **No Critical tile or badge.** Criticality is parked, so recommend three tiles (Open,
   Answered this week, Parked), with no Critical badge on cards.
2. **"Most important first"** without criticality: recommend more calls seen first,
   then money, safety or compliance, then the newest. The design adds "whether a
   critical issue depends on it", which waits for criticality. The same order applies
   in `list_clarifications` for open questions.
3. **Confirm before an answer is recorded?** The design answers with one click. An
   answer is final, and it writes a rule. Recommend a one-step confirm in the card that
   shows the rule it writes.
4. **Reopen a parked question.** Part 1 decided that a parked question is reopened by
   answering it. The design has a "Reopen" button that puts it back in the open list.
   Recommend adding `reopen` (parked to open, recorded) to the same service and to
   `answer_clarifications`, rather than a new tool.
5. **The batch confirm flow** (the assistant prepares answers and the person confirms a
   batch in the app) is in this row "unless Dmytro moves it". It needs Connexity to store
   the assistant's suggested answers, which is a model change of its own. Recommend
   moving it to its own row after this one. Today the assistant confirms the batch in
   its session, as the tool rules say. (Done: it is row 10.123.)
6. **"N more"** shows 5 more each time, so the person never faces them all at once.
   Recommend yes.
7. **A conflict's quotes.** The design quotes the earlier answer and the new prompt.
   Connexity has the earlier answer (the rule, who and when), but not the new prompt's
   words: the spec guide asks the assistant to quote them in the question. Recommend
   quoting the earlier answer only.

## Done when

- **The web routes,** played through on the local database with throwaway data:
  - list in importance order, with counts and `answered_since`;
  - answer and park;
  - reopen;
  - every refusal, and another workspace's.
- **`reopen` and the importance order through MCP.**
- **`make check` passes.**
- **For Dmytro on screen:**
  - the page with five or more open questions: the tiles, the top 5 with "N more", a
    conflict card;
  - answering with the confirm;
  - parking, then reopening from Parked;
  - the Answered section;
  - the agent filter, and arriving from the Spec tab;
  - the sidebar count;
  - dark and light.

## Out of scope

- The batch confirm flow and stored suggested answers: its own row, 10.123 (question 5).
- Criticality and severity (parked).
- Other item kinds (archive proposals, check settings, versions without passing tests).
- Home and Incidents in the sidebar.

## Risks

- **An answer in the app is final.** Hence the confirm (question 3), and the rule text
  is shown before it is recorded.
- **The sidebar count** adds one count query to every page load. It is a single grouped
  count.

## Outcome

### Deviations from the plan

- **"Answered this week"** is filtered by the backend (`this_week` on
  `GET /clarifications`). The frontend lint rule forbids reading the clock during
  render.
- **One agent's list** shows 50 at first, then 5 more each time, up to 200 a page, so
  every question stays reachable (found in review).
- **A failed Reopen says so** in the Parked section (found in review).
- **The web route's cursor** is its own small encoder, not the MCP one. It is left as it
  is (review finding: the two formats could drift).
- **#205 had merged** before this was built, so the branch was rebased onto `main`.
- **The batch confirm flow** became row 10.123 in the roadmap, as question 5 proposed.

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

API play-through on the local server (`:8027`, local database). The throwaway workspace
had an invented agent, one spec, and seven open questions: five plain ones, one seen on
two calls, and one touching money. It was deleted afterwards:

| # | Request | Expected | Came back |
|---|---|---|---|
| 1 | `GET /clarifications` | 5 shown, most important first, more to come | 200; 5 shown; first seen on 2 calls, then the money one; open 7; next_cursor set |
| 2 | The next page | the other 2 | 2 shown; next_cursor empty |
| 3 | `POST /clarifications/answers` with b and park | 1 answered, 1 parked, spec version 2 | answered 1, parked 1, open 5; version 2 with 1 rule added |
| 4 | Answered this week | 1, with no assistant | 1 item; answered_this_week 1; assistant none |
| 5 | Reopen the parked one | back to open | reopened 1; open 6 |
| 6 | Answering the answered one again | 422 | 422; "already answered (b)" |
| 7 | Filtering by an unknown agent | 404 | 404 |
| 8 | The spec after answering in the app | the rule, written by the person, no assistant | from clarifications 1; written_by set; assistant none |
| 9 | MCP `list_clarifications` | the same order, and the rule saying it | the money one first among those without calls; the rule is present |

The server log has no errors.

Tests:
- `app/tests/api/routes/test_action_items.py` (2 tests): listing, answering, parking
  and reopening as the person; refusals and other workspaces.
- `app/tests/services/test_clarifications.py` gains reopen and the importance order.

**For Dmytro to check on screen:**
1. **`/action-items`** with six or more open questions:
   - the tiles Open, Answered this week and Parked;
   - the caption;
   - the top 5 and "N more";
   - the cards: agent link, kind, question, evidence, "Open a call", answers a to d with
     their rule on hover, and Park.
2. **A conflict card** (a question that replaces a rule): "Conflict with an earlier
   answer", with the earlier answer quoted.
3. **Answering:** pick an answer, see the confirm with the rule, then Confirm. The card
   leaves the list, Answered this week goes up, and the rule shows on the agent's Spec
   tab as answered by you.
4. **Park, then Reopen** from the Parked section.
5. **The Agent picker,** and arriving from the Spec tab's Open clarifications tile or "Open
   the clarification".
6. **The sidebar:** "Action items" first, with its open count, and no count when none are
   open.
7. **Dark and light.**

### Not done

- Other kinds of action item, criticality, and the batch confirm flow (10.123).
- One cursor format for web and MCP (review finding).
