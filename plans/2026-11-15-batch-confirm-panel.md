# Suggested answers, part 2: the batch panel

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Batch confirm of suggested answers"
  (10.123), part 2 of 2. Part 1 (suggestions stored and shown, backend and MCP) is
  Connexity-AI/connexity#207. Planned in `plans/2026-11-15-batch-confirm.md`, which
  Dmytro accepted ("Accept, build part 1"; then "build part 2" with the design).
- **Design:** `designs/14-suggested-answers.md`, built in Claude Design and exported as
  `designs/screens/Connexity Action items.dc.html` (design review 6, 2026-11-15).
- **MCP:** none new. The assistant already suggests through `raise_clarifications`
  (#207). The web list gains a filter for confident suggestions; nothing a tool does
  changes.

## Goal

On Action items, the person confirms the assistant's confident suggestions in one batch
and sees the unsure ones on their cards. Only confirmed answers become spec rules. With
this, 10.123 is done.

## Changes

### The batch panel (design section 1)

- **When it shows:** above the cards, when any open question (for the picked agent, if
  one) has a confident suggestion.
- **The header:**
  - "Your assistant suggests answers for 6 questions it is confident about.";
  - the muted line "Check them, then confirm. Each becomes a rule in its agent's spec.";
  - clicking the header collapses or opens the panel.
- **Rows:**
  - one per confident suggestion, ticked by default, with a click toggling the tick;
  - each row shows the agent, the question in one line (full text on hover), the
    suggested answer's label, and under it "the rule · the why".
- **More than 10:** the first 10, then "and 14 more", which shows the rest.
- **Buttons:**
  - "Confirm 6 answers", following the ticks and disabled at 0, sends the ticked
    answers in one request, which makes one spec version per agent;
  - "Review one by one" collapses the panel.
- **After confirming:** the panel goes, and the muted line "6 answers confirmed · added
  to 2 agents' specs" shows in its place.

### A suggestion on a card (design section 2)

- **Which cards:** a card shows its suggestion when it is unsure, when it was unticked,
  or when the panel is collapsed.
- **The line:** "Your assistant suggests b: Only when the caller asks · not sure: the
  prompt says nothing", with "not sure:" only for an unsure suggestion.
- **The suggested button** has an accent outline and a "Suggested" label. Picking any
  answer opens the same confirm as today.

### Answered (design section 3)

An answer confirmed from a suggestion reads "Dmytro, suggested by your assistant, 15
Nov".

### The API

`GET /clarifications` gains `confident=true`: open questions with a confident
suggestion only, up to 200. The panel reads all of them, not only the top 5 on the
page.

## Decisions

- **As designed,** with one difference: no Critical tile. Criticality is parked,
  Decided 2026-11-11, and the 10.122 plan applied it.
- **Unticking keeps a suggestion as a suggestion.** The person decides it on its card.

## Done when

- **The panel, cards and Answered line** match the export.
- **Confirming a batch** of three across two agents makes one spec version per agent.
  The API play-through shows this.
- **`make check` passes.**
- **The screens are listed** for Dmytro to check.

## Out of scope

- Suggesting on questions raised earlier.
- Criticality.
- Other kinds of action item.

## Risks

- **Rubber-stamping.** Each row shows the rule it writes and the why, and only confident
  suggestions are ticked.

## Outcome

### Deviations from the plan

- **The confirmed line** ("4 answers confirmed · added to 2 agents' specs") also shows
  while unticked suggestions keep the panel open, not only once the panel goes (found
  in review).
- **A refused batch** (one answered elsewhere since the page loaded) reloads the list
  and says nothing was recorded, so the person can confirm the rest (found in review).
- **Colours:** the checkbox, Confirm button and suggested outline use the design
  system's accent (`accent-ink` with `on-accent`), as the export does.
- **Only the Action items screen** was taken from design review 6. The Roadmap and
  overview changes in the same export belong to 10.124 and are left for it.

### Check results

`make check`:

| Gate | Result |
|---|---|
| Plan present and complete | ok (after this Outcome) |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok (run again after the review fixes) |
| Frontend types | ok (run again after the review fixes) |
| Generated client is fresh | ok |

API play-through on the local server (`:8027`, local database). The throwaway workspace
had two invented agents, each with a spec, and four questions:
- three with confident suggestions, two on one agent and one on the other;
- one unsure.

It was deleted afterwards:

| # | Request | Expected | Came back |
|---|---|---|---|
| 1 | `GET /clarifications?confident=true` | the 3 confident ones | 3 in the batch; suggested_confident 3; open 4 |
| 2 | Confirming the batch of 3 in one request | one spec version per agent | answered 3; front desk version 2 with 2 rules, night line version 2 with 1 rule; open 1 |
| 3 | The batch afterwards | empty; the unsure one still open | 0 left; the unsure one still open |
| 4 | Answered this week | 3, all from a suggestion | 3; all from_suggestion |

The server log has no errors.

`app/tests/api/routes/test_action_items.py` gains a batch of confident suggestions
across two agents.

**For Dmytro to check on screen** (`/action-items`, with the assistant having raised
questions with suggestions):
1. **The panel:**
   - "Your assistant suggests answers for N questions it is confident about." and the
     muted line;
   - rows ticked by default (click toggles), with agent, question, answer, and "rule ·
     why";
   - "and N more" past 10;
   - "Confirm N answers" following the ticks;
   - "Review one by one" collapses it, and so does the header.
2. **Confirm:** the panel goes, "N answers confirmed · added to M agents' specs" shows,
   the questions move to Answered, and the rules show on each agent's Spec tab.
3. **Cards:**
   - an unsure suggestion shows "Your assistant suggests b: … · not sure: …", with the
     suggested button outlined and "Suggested";
   - an unticked or collapsed confident one shows its line without "not sure";
   - a ticked one in the open panel shows no line on its card.
4. **Answered:** "Dmytro, suggested by your assistant, 15 Nov".
5. **The Agent picker** narrows the panel too.
6. **Dark and light.**

### Not done

- Suggesting on questions raised earlier.
- Criticality (the export's Critical tile stays out, as decided).
