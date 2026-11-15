# Suggested answers, confirmed in a batch

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Batch confirm of suggested answers"
  (10.123), right after the Action items page (10.122,
  Connexity-AI/connexity#206). This branch is cut from #206's and is rebased onto `main`
  once that merges.
- **Design:** none exists yet. The prompt for Claude Design is
  `designs/14-suggested-answers.md` (question 5). It covers the batch panel on Action
  items, a suggestion on a card, and "suggested by your assistant" in Answered.
- **MCP:**
  - `raise_clarifications` gains an optional suggestion per question (question 1);
  - `list_clarifications` shows suggestions;
  - the spec guide's "Answering" section describes suggesting.

## Goal

The assistant does the work of preparing answers ("I can answer 75 confidently; I need
your help with the other 7"). Connexity keeps those suggestions, and the person confirms
the confident ones in one batch in the app, deciding the rest themselves. Only a
confirmed answer becomes a spec rule, so clarifications are still never answered without
the person (Decided, `designs/who-does-what.md`).

## What exists

- **Clarifications** (10.12): raised with two to four answers, each carrying its rule.
  They are answered, parked or reopened, and answers make one spec version per agent.
  Every decision is recorded.
- **Action items** (10.122, #206): the person answers one question at a time, with a
  confirm in the card.
- **Today the assistant** confirms a batch with the person in its session, then calls
  `answer_clarifications`.

## Changes

### A suggestion

Each clarification can carry one suggestion:
- `suggested_answer`: a letter a to d;
- `suggestion_why`: one plain sentence, at most 300 characters;
- `suggestion_confident`: true or false (question 2);
- who suggested it (the person whose assistant raised it, and the assistant) and when.

A suggestion changes nothing in the spec. It is cleared when the question is answered
or parked.

### MCP

- **`raise_clarifications`:** each question may carry `suggested_answer`, `why` and
  `confident`. It is refused if the letter is not one of the question's answers, or if
  `why` is missing or too long.
- **`list_clarifications`:** each item shows its suggestion. The counts gain
  `suggested_confident`.
- **The rules and guide:** suggest only what the prompt or the calls support, mark
  `confident` only when the prompt or a clear pattern on calls settles it, and never
  treat a suggestion as an answer. The person confirms in the app, or the assistant
  confirms with them in its session and calls `answer_clarifications`, as now.

### The web app (after the design, question 5)

- **The batch panel:**
  - it sits at the top of Action items when any open question has a confident
    suggestion;
  - each suggestion is ticked by default;
  - "Confirm N answers" sends the ticked ones in one `POST /clarifications/answers`,
    which already makes one spec version per agent.
- **A card with a suggestion** shows it, and its button is marked "Suggested". Picking
  an answer opens the same confirm as today.
- **Answered** says "suggested by your assistant" for an answer confirmed from a
  suggestion.

### Data

The `clarification` table gains `suggested_answer`, `suggestion_why`,
`suggestion_confident`, `suggested_by` (user), `suggested_assistant` and `suggested_at`
(migration `0022`). When the person confirms, the answer records them as the one who
answered and the suggesting assistant as `decided_assistant` (question 4). The decision
record's `detail` notes that it came from a suggestion.

## Decisions

- **Clarifications are never answered without the person;** the assistant prepares
  answers and the person confirms the batch. Decided (`designs/who-does-what.md`).
- **The batch confirm flow is its own row,** 10.123. Decided (Dmytro, 2026-11-15, via
  the 10.122 plan).
- **UI changes start in the design.** Decided (`CLAUDE.md` rule 9). Hence question 5.
- Everything under "Questions" is Proposed until Dmytro answers.

## Questions

1. **Where a suggestion comes from.** Recommend an optional suggestion on each question
   of `raise_clarifications`. The assistant prepares its answer when it raises the
   question, so no new tool is needed (rule 10: few tools). The alternative is a
   separate `suggest_answers` tool, for suggesting on questions raised earlier.
2. **How confident is said.** Recommend a plain true or false that the assistant sets,
   with its one-sentence why. A score would look more precise than it is.
3. **What the batch holds.** Recommend only the confident suggestions. The person
   decides the rest one card at a time, with the suggestion shown.
4. **Who an answer from a suggestion records.** Recommend the person as the one who
   answered, and the suggesting assistant as the assistant. It reads "Answered by
   Dmytro, suggested by your assistant".
5. **Order of work.** The design does not exist yet. Recommend two parts:
   - **part 1 now:** the data, the suggestion on `raise_clarifications`, and
     `list_clarifications` and the web list showing suggestions. That is backend and
     MCP, with no UI.
   - **part 2 after you bring back the design** from `designs/14-suggested-answers.md`:
     the batch panel and the card.

   The alternative is to wait for the design and build both at once.

## Done when

**Part 1:**
- through the MCP API on the local database: raise with suggestions (confident and not);
- one refused for a letter that is not an answer;
- `list_clarifications` shows them with `suggested_confident`;
- answering one from a suggestion records the person and the suggesting assistant;
- `make check` passes.

**Part 2:**
- the panel and cards match the exported design;
- confirming a batch of three across two agents makes one spec version per agent;
- the screens are listed for Dmytro to check.

## Out of scope

- Connexity suggesting answers itself (no model in Connexity).
- Suggestions on the other kinds of action item.
- Criticality (parked).

## Risks

- **Rubber-stamping.** A one-click batch makes it easy to confirm without reading.
  Each row shows the rule it writes and the why, and nothing is ticked unless the
  assistant marked it confident.
- **A suggestion read as an answer.** Every MCP rule and the guide say a suggestion
  changes nothing until the person confirms.

## Outcome

Part 1 only (backend and MCP). Part 2, the batch panel and the card, waits for the
design from `designs/14-suggested-answers.md`.

### Deviations from the plan

- **A suggestion is kept after the answer, not cleared.** The plan said it would be
  cleared once the question is answered or parked. Keeping it lets the record say an
  answer came from a suggestion: `from_suggestion` on the list, and `from_suggestion`
  in the decision record's `detail`. `suggested_confident` counts open questions only,
  so the batch never holds an answered one.
- **An answer given in the app with the suggested letter** records the suggesting
  assistant as `decided_assistant`. An answer through MCP keeps the assistant that sent
  it.
- **Review findings:**
  - the suggestion fields were set through a dict splat; they are now set plainly
    (fixed);
  - when a different assistant confirms a suggestion through MCP, the record names
    that assistant. The suggester stays on the suggestion itself, which is enough for
    now (left).
- **#206 had merged** before this was built, so the branch was rebased onto `main`.

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
had an invented agent, one spec, and two questions: one with a confident suggestion,
one with an unsure suggestion. It was deleted afterwards:

| # | Request | Expected | Came back |
|---|---|---|---|
| 1 | `raise_clarifications` with two suggestions | stored, letters made lower case | 200; c confident, b not confident; assistant set |
| 2 | A suggestion that is not an answer | 422 | 422; "the suggested answer 'd' is not one of its answers (a, b)" |
| 3 | The spec after suggesting | unchanged | version 1; no rules from clarifications |
| 4 | `GET /clarifications` | 1 confident; both show their suggestion | suggested_confident 1; suggestions on 2 of 2 |
| 5 | The person confirms c, and picks a against the other's suggestion | one spec version with 2 rules | answered 2; version 2 with 2 rules added |
| 6 | The answered list | one from a suggestion (with its assistant), one not | (true, assistant set) and (false, none) |
| 7 | MCP `list_clarifications` rules | the suggestion rule | present |

The server log has no errors.

Tests: `app/tests/services/test_clarifications.py` gains a suggestion that waits and is
then confirmed, and a bad suggestion refused. `test_mcp_clarifications.py` gains a
suggestion through MCP.

There is no screen in this part.

### Not done

- **Part 2:** the batch panel and the suggestion on a card, once the design is back.
  10.123 is done when it merges.
- **Suggesting on a question raised earlier** (question 1 chose suggestions at raise
  only).
