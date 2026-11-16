# Remove suggested answers

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Remove suggested answers" (10.123). It
  replaces "Batch confirm of suggested answers": part 1 (#207) is merged, and part 2
  (#208) is closed without merging.
- **Design:** `docs-internal/work.md` decision 13 and `designs/16-work.md` (no suggested
  answers, no confirm screen). `designs/14-suggested-answers.md` is superseded.
- **MCP:** `raise_clarifications` loses its suggestion arguments, and
  `list_clarifications` loses the suggestion and its count. The assistant still
  answers through `answer_clarifications`, after asking the person in its own chat.

## Goal

Connexity does not store or show answers suggested by an assistant. Dmytro, 2026-11-16:
"I dont want to translate AI Assistant suggestions to Connexity - it becomes loop in a
loop insanity". The assistant asks the person in its own chat and submits what they
pick. In Connexity, the person answers manually. Done when no suggestion is stored,
accepted through MCP or shown (roadmap row).

## What exists

Part 1 (#207, migration `0022_clarification_suggestion`) added:
- **Six columns on `clarification`:** `suggested_answer`, `suggestion_why`,
  `suggestion_confident`, `suggested_by` (a foreign key and an index), `suggested_assistant`
  and `suggested_at`.
- **`raise_clarifications` arguments:** `suggested_answer`, `why` and `confident`, with
  their checks.
- **The answers:** `suggestion` and `from_suggestion` on each clarification, and
  `suggested_confident` in the counts.
- **Two writes from a suggestion:**
  - `from_suggestion` in the decision record's detail;
  - `decided_assistant` falls back to the suggesting assistant when the person answers in
    the app.
- **Texts:**
  - a rule in `_CLARIFICATION_RULES`;
  - `raise_clarifications`'s next step ("Your suggestions also wait for them on the
    Action items page");
  - the tool description in `app.py`;
  - the spec guide's "Suggesting an answer".

The app shows no suggestion: the panel was in #208. The hosted database is at `0022`
and holds no clarifications, so dropping the columns loses nothing (read only, counts).

## Changes

### Schema

- **Migration `0023_drop_suggestion`** drops the six columns, the foreign
  key and the index. Its downgrade adds them back, empty.
- **`Clarification`** loses the six fields.

### Logic

- **`QuestionDraft`** loses `suggested_answer`, `suggestion_why` and
  `suggestion_confident`. `raise_clarifications` loses their checks and their writes.
- **`answer_clarifications`:**
  - `decided_assistant` is the assistant that acted, or none when the person answers in
    the app;
  - the decision record no longer carries `from_suggestion`.
- **Removed outright:**
  - `crud.confident_suggestions`;
  - `SuggestionPublic`;
  - `ClarificationPublic.suggestion` and `from_suggestion`;
  - `ClarificationCountsPublic.suggested_confident`.

### MCP

- **Request:** `McpRaiseClarifications`'s question drops `suggested_answer`, `why` and
  `confident`. The same goes for the adapter's models and the `raise_clarifications`
  description.
- **Response:** the adapter's `Suggestion`, `from_suggestion` and `suggested_confident`
  go (question 2).
- **The suggestion rule leaves `_CLARIFICATION_RULES`.** The answering rule stays:
  confirm every answer with the person before `answer_clarifications`.
- **`raise_clarifications`'s next step** reads: "Ask the person in your chat, one
  question at a time or in one batch, then call `answer_clarifications` with what they
  pick. Never answer without them. They can also answer in Connexity." The words "in one
  batch, say which you can answer confidently" go from the rules too (question 3).
- **The spec guide:**
  - "Suggesting an answer" is removed;
  - "Answering" says the assistant may tell the person what it would pick and why, in
    its chat. Connexity records only the answer.

### Frontend

The generated client only (`make generate-client`). No screen shows suggestions on
`main`.

### Docs

- **`docs-internal/data-model.md`:** the `clarification` row loses the suggestion.
- **`REBUILD.md`:** the 10.123 row becomes "Remove suggested answers", with a decision
  log line.
- **`designs/14-suggested-answers.md` is deleted** (question 1). `designs/README.md` drops
  it.
- **`docs-internal/work.md`:** Open item 1 is settled by the roadmap row and leaves the
  list.

## Decisions

- **Remove suggestions everywhere:** stored fields, MCP arguments and anything shown.
  Decided (Dmytro, 2026-11-16, roadmap row and `work.md` decision 13).
- **The assistant still answers through `answer_clarifications`,** after asking the
  person in its chat. Decided (roadmap row).
- **The columns are dropped by a new migration, not by editing `0022`,** because the
  hosted database has run `0022`. Applies rule 7, delete, do not deprecate.
- Everything under "Questions" is Proposed until Dmytro answers.

## Questions

1. **`designs/14-suggested-answers.md`.** Rule 7 says ask before deleting what
   `REBUILD.md` does not list. Recommend deleting it: `16-work.md` replaces it, and a
   superseded prompt in `designs/` invites building it. `plans/2026-11-15-batch-confirm.md`
   stays, because it is #207's merged plan.
2. **A stale assistant sending `suggested_answer`.** Today unknown arguments are
   ignored, so an old client's suggestion would be dropped silently. Recommend that:
   nothing is stored, and the next step already says to ask the person. The alternative
   is refusing unknown arguments on this one tool, which no other tool does.
3. **"Say which you can answer confidently"** in the answering rule came with
   suggestions. Recommend dropping it: whether the assistant asks one at a time or in a
   batch is for its chat, not Connexity. Keep "Never answer without them".

## Done when

- **Through the MCP API** on the local database, with throwaway data:
  - `raise_clarifications` stores a question, with no suggestion in the answer;
  - `list_clarifications` has no `suggestion`, `from_suggestion` or
    `suggested_confident`;
  - `answer_clarifications` answers it and writes the spec version as before.
- **`alembic upgrade head` and `downgrade -1`** both run on the local database.
- **No "suggest" is left** in the clarification code, the MCP server or the guides.
  Unrelated 1.x run suggestions are not touched.
- **`make check` passes.**

## Out of scope

- Answering on Work (10.128), and removing the Action items page with it.
- Anything about `get_next_task` (10.124).

## Risks

- **The downgrade** brings back empty columns only; suggestions are gone for good.
  Nothing on the hosted database is lost.
- **An assistant reading old guide text** from its cache may still send suggestions.
  They are ignored (question 2).

## Outcome

### Deviations from the plan

- **The migration is `0023_drop_suggestion`:** the longer planned name did not fit
  Alembic's 32-character revision column.
- **The getting-started guide** also loses "confirm the answers with the person in one
  batch" (a review finding, fixed).
- **`docs-internal/work.md`'s Open list now starts at 2.** Renumbering would break
  references such as `frontend/CLAUDE.md`'s "open question 11".
- **Review finding left as it is:** an MCP answer from a client that sends no assistant
  name is recorded as "your assistant". This was the behaviour before #207.

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

The local Postgres container had been recreated from another checkout with a different
password, so the tests ran with `TEST_DATABASE_URL` pointing at it.

**Migration:** on the local database, `alembic upgrade head`, `downgrade -1` and
`upgrade head` all ran, and `alembic check` found no drift.

**API play-through** on the local server (`:8027`, local database). The throwaway
workspace had an invented agent, prompt and two calls, and was deleted afterwards:

| # | Request | Expected | Came back |
|---|---|---|---|
| 1 | `raise_clarifications`, one question with an old client's `suggested_answer`, `why` and `confident` | stored, the suggestion ignored | 200; 2 stored; no suggestion field; no rule mentions a suggestion |
| 2 | `list_clarifications` | no suggestion count or field | open 2; counts open, answered, parked, answered_this_week; no suggestion keys |
| 3 | `answer_clarifications` (b, park) | one answered, one parked, a spec version | 200; answered 1, parked 1; spec version 2 with 1 rule added |
| 4 | Web `GET /clarifications?state=answered` | no suggestion field | 1 row; no suggestion keys |
| 5 | The table and the decision record | no suggestion columns; detail without `from_suggestion` | 0 columns; detail keys rule, spec_version |

The server log has no errors.

Tests:
- `test_an_answer_in_the_app_names_no_assistant` replaces the suggestion tests in
  `app/tests/services/test_clarifications.py`;
- `test_a_suggested_answer_is_not_stored` in
  `app/tests/api/routes/test_mcp_clarifications.py`.

There is nothing to check on screen: no page showed suggestions.

### Not done

- Answering on Work, and removing the Action items page: 10.128.
