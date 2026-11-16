# Questions as cards on Work

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Questions as cards on Work" (10.128).
- **Design:** `designs/16-work.md` ("Waiting for you", frames 4 and 5) and
  `docs-internal/work.md` decisions 12 to 15. Screen: `designs/screens/Connexity
  Work.dc.html`, the answering frames: the cards under the waiting row, the choices,
  "Something else" with "Save answer", "2 of 3", Back and Skip.
- **MCP:** nothing new. The assistant keeps `list_clarifications` and
  `answer_clarifications`, and gains "something else" answers (question 2).

## Goal

The person answers the questions blocking their assistant right on Work, one card at a
time, in seconds. Their answers go into the agent's spec, and the tasks they blocked
unlock. Action items folds into Work and is deleted (decision 12).

## What exists

- **Answering:** `POST /clarifications/answers` (web) and `answer_clarifications` (MCP)
  answer a to d, park and reopen. Answers for one agent, given together, make one spec
  version.
- **Work** shows "Answer 3 questions about Front desk" as waiting, with "Answer
  questions →" linking to Action items.
- **Action items** (10.122): the page, its sidebar entry and count, and the Spec tab's
  links to it.

## Changes

### The cards

- **"Answer questions →" opens the agent's open questions under its row,** one card at
  a time, most important first, as on Action items. Each card has:
  - the question in one plain sentence;
  - one muted line on why it was asked: "Seen on 9 calls", or "Raised from the prompt";
  - for a question that replaces an earlier answer, one muted line quoting it
    (question 5);
  - the choices as large tappable options, then "Something else", which opens a text
    field and "Save answer";
  - "2 of 3", Back and Skip.
- **Picking a choice** marks it, as the design does, and moves to the next card.
  - **Back** returns to the previous card, where the choice can still change.
  - **Skip** leaves the question open.
- **After the last card,** every choice is sent together (question 1). The answers
  become rules in one spec version, the row leaves the list, and the tasks it blocked
  unlock.
- **The waiting row's link,** the side panel's link, and `/work?answer=<agent id>` all
  open the cards. The Spec tab's links use the last of these.
- **On Work, answers stay barely visible** (decision 15): one row in "done this week",
  "3 answers added to the Front desk spec". The rest is in the spec.

### "Something else"

- **The person's own words become the rule** (question 2). The answer is recorded as
  "other" with its text, in the question's category and with its touches.
- **The field's hint:** "Write it as the rule the agent should follow."
- **The backend:**
  - `clarification` gains `answer_text`, through migration `0027`;
  - both answer routes, web and MCP, take `answer: "other"` with `text`;
  - the spec's rule from it reads "From a clarification".

### Deleting Action items

- **Deleted** (question 4):
  - the `/action-items` page and `action-items-view.tsx`;
  - its sidebar entry and count, and the layout's open-questions read;
  - `UrlGenerator.actionItems`.
- **`GET /clarifications` loses `this_week`,** which only Action items used. The cards
  read the open questions with the same route.
- **The Spec tab's** Open clarifications tile and "In conflict" line link to
  `/work?answer=<agent id>`.
- **`designs/README.md`** marks the Action items screen deleted, not only superseded.

## Decisions

- **The cards as designed,** in Dmytro's words: "less then 4 so we can show them one by
  one as tinder cards". Decisions 12 to 15.
- **No suggested answers** (decision 13).
- Everything under "Questions" is Proposed until Dmytro answers.

## Questions

1. **When answers are saved.** Recommend sending them together after the last card.
   That makes one spec version per agent, as answers do today, and Back can still change
   a choice. The alternative is saving each pick at once: then an answer is final as
   soon as it is tapped, Back only shows it, and each answer makes its own spec version.
   With the recommendation, leaving midway keeps nothing.
2. **"Something else".** Recommend that the person's text becomes the rule as written.
   The person decides; the hint asks for a rule. The alternative is parking the question
   with their note, so the assistant raises a better question with that answer. That is
   one more round before anything is settled.
3. **No Park on the cards.** The design has none. Recommend Skip for "not now", which
   leaves the question open, and park only through the assistant. Parked questions are
   then reachable only through MCP (`list_clarifications`, `reopen`). Questions parked
   today stay parked.
4. **Delete Action items now.** Rule 7 asks before deleting what `REBUILD.md` does not
   list. Recommend deleting the page, its entry, its component and the `this_week`
   parameter. Its Answered list and Reopen go with it; answers live in the spec and in
   "done".
5. **The earlier answer on a replacing question.** The design's cards do not show it.
   Recommend one muted line, "Earlier answer: …", as Action items has. Without it, the
   person cannot see what they are changing.

## Done when

- **Through the API,** in the route tests on the local database:
  - an "other" answer with text becomes a rule in the agent's spec, in one version with
    the lettered answers given beside it;
  - "other" without text is refused;
  - `answer_clarifications` through MCP takes "other" the same way.
- **`make check` passes** once, before the pull request (CLAUDE.local.md).
- **For Dmytro on screen:**
  - "Answer questions →" opens the cards;
  - picking moves on, and Back changes a choice;
  - Skip leaves a question open;
  - "Something else" saves its text;
  - after the last card, the row leaves and the blocked tasks unlock;
  - `/work?answer=<agent id>` from the Spec tab;
  - Action items is gone from the sidebar.

## Out of scope

- Parking and reopening on screen (question 3).
- Onboarding as Work's rows (10.129).
- A cap on how many questions the assistant raises per fix (`work.md` open question 3).

## Risks

- **Leaving midway** loses the choices made so far, with the recommendation in
  question 1. The cards are short (under 4 per fix), so this costs little.
- **Free-text rules** may read less clearly than the assistant's. The spec shows them
  as the person's, and a later question can replace them.

## Outcome

### Deviations from the plan

- **`clarification.answer` widens from one character to 8** to hold "other", in the
  same migration `0027` as `answer_text`. Its downgrade turns "other" into "o" and drops
  the text.
- **`list_page` loses `decided_since`** along with the route's `this_week`; nothing else
  used it.
- **`test_action_items.py` became `test_question_cards.py`,** with two new tests.
- **Review findings:**
  - **Fixed:** going Back to a "Something else" card left "Save answer" disabled.
  - **Left as they are:** leaving midway loses the choices (question 1's trade-off), and
    the downgrade above.

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

`pnpm --filter connexity build` passes; `/action-items` is gone.

Per CLAUDE.local.md, while building only the touched test files ran:
- `test_question_cards.py`, `test_mcp_clarifications.py` and `test_clarifications.py`;
- the MCP server tests.

Then the full `make check` ran once. No separate play-through server: the route tests
send the same requests through the API.
- "Other" with the person's words becomes a rule in one spec version with a lettered
  answer given beside it.
- "Other" without text is refused.
- MCP `answer_clarifications` takes "other" the same way.

**For Dmytro to check on screen** (`/work`):
1. **The sidebar** has no Action items; Work keeps its warm count.
2. **On a waiting "Answer N questions about …" row,** "Answer questions →" opens the
   cards under the row. Each card shows:
   - the question;
   - "Seen on N calls" or "Raised from the prompt";
   - for a question that replaces an earlier answer, "Earlier answer: …";
   - the choices, then "Something else".
3. **Picking a choice** moves to the next card. "2 of 3" counts. Back returns with the
   choice still marked, and changing it works. Skip leaves a question open.
4. **"Something else"** opens a field ("Write it as the rule the agent should follow.")
   and "Save answer". Going Back to it shows the words again.
5. **After the last card,** the row leaves the list, the tasks it blocked lose their
   lock, and "done this week" gains "N answers added to the … spec". The agent's Spec
   tab shows the new rules, the person's own words as written.
6. **The side panel's "Answer questions →"** and the Spec tab's Open clarifications tile
   and "In conflict" link open the same cards (`/work?answer=<agent id>`).

### Not done

- Parking and reopening on screen (question 3).
- The two review findings left above.
