# Clarifications, part 2: MCP

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Clarifications in Action items" (10.12),
  part 2 of 3 (Decided, Dmytro: schema and logic first, then MCP, then the page). Part 1
  is Connexity-AI/connexity#203. Part 3, the Action items page, comes after the demo.
- **Design:** no UI change.
- **MCP:**
  - adds `raise_clarifications`, `list_clarifications` and `answer_clarifications`;
  - `get_spec` gains the open count, and `write_spec`, `get_spec`, `get_agent`,
    `get_issue` and `get_readiness` gain next steps;
  - the server instructions gain one line;
  - the spec guide gains how to raise and answer questions.

## Goal

The assistant can do in Claude Code what part 1 made possible. It raises a question when
the spec leaves behaviour unsettled, confirms the answers with the person, and submits
them, which adds the rules to the spec. This is demo step 4: the person answers in
Claude Code. Connexity's answers tell the assistant when to raise questions, so it does
not have to remember to.

## What exists after part 1

- **`raise_clarifications`** (service): stores all the questions or none, and lists
  every problem. It needs a spec.
- **`answer_clarifications`** (service): answers (a to d) and parks. Answers for one agent
  make one spec version, and every decision is recorded.
- **Counts:** open per agent, and open, answered and parked per workspace or agent.
- **`write_spec`** carries answered rules over and refuses them, and its answer counts
  them (`changes.carried`).
- **Errors** use the standard answer: `McpErrorDetail` with the problems as next steps,
  as `write_spec` does.

## Changes

### `raise_clarifications(workspace_id, agent_id, questions)`

- **Each question** has:
  - `question`: one plain sentence;
  - `answers`: two to four, each a `label` and the `rule` it becomes;
  - `category`: a key from `list_categories`;
  - `touches`: optional;
  - `call_ids`: optional, at most 50;
  - `replaces_key`: optional, the key of a spec rule the answer replaces.
- **At most 20 questions** per call, for one agent.
- **Refused with 422,** listing every problem from part 1, nothing stored.
- **Answers** the stored questions as `list_clarifications` shows them. The next step
  is: "Confirm the answers with the person in one batch: say which you can answer
  confidently and which need them, then call `answer_clarifications`. Never answer
  without them."
- **Annotation:** `CREATES`, like `write_spec`.

### `list_clarifications(workspace_id, agent_id?, state?, cursor?)`

- **Open by default.** `state` is open, answered or parked. Newest first, 20 per page,
  paginated with `next_cursor` like the other lists.
- **Each item has:**
  - its id, agent id and name;
  - the question;
  - the answers as `a` to `d`, each with its label and rule;
  - the category key and name, and `touches`;
  - `calls_seen` and the `call_ids`;
  - the spec version it was raised against;
  - for a replacing question, the key and the current text of the rule it replaces;
  - who raised it and when;
  - once answered, the chosen letter, who answered (the person, and the assistant that
    acted) and when, and the spec version it made;
  - once parked, who parked it and when.
- **Counts** of open, answered and parked for the same filter come with every page.
- **Annotation:** `READ_ONLY`.

### `answer_clarifications(workspace_id, answers)`

- **Each item** has a `clarification_id` and an `answer`: `a` to `d`, or `park`. At
  most 50 per call. They may span agents.
- **Refused with 422,** listing every problem from part 1, nothing stored.
- **Answers:**
  - per agent, the new spec version and the rules it added;
  - how many were answered and parked;
  - the counts still open.
- **Next steps:** tell the person what was recorded, and that their answers are now spec
  rules that carry into every later version. If any remain open, say how many.
- **Rules:**
  - "The person answers. Confirm every answer with them before calling this. When they
    leave a decision to you, it is still recorded as theirs, with you as the assistant
    that acted; tell them so." (question 1)
  - "An answer is final. To change one, raise a clarification that replaces its rule."
- **Annotation:** `DECIDES`, like archiving.

### What the assistant is told, and where

From the plan of part 1, "How the assistant knows":

1. **Server instructions** gain: "Behaviour an agent's spec does not settle is a question
   for the person: raise it with `raise_clarifications`, never decide it."
2. **The spec guide** replaces "Until Connexity has clarifications, list the questions"
   with a section "Questions for the person". It covers:
   - check `list_clarifications` first;
   - one question, one behaviour, with how often it happened ("on 9 of 120 calls");
   - two to four realistic answers, and a rule for each, since there is no "doesn't
     matter";
   - the calls as evidence, or none for a prompt change;
   - replacing an answered rule a new prompt contradicts, quoting the earlier answer and
     the new prompt in the question;
   - one confirmed batch;
   - rules from answers are carried over: never pass them to `write_spec`.
3. **Next steps at the triggers:**
   - **`write_spec`** (trigger 1) replaces "list the behaviour ... as questions" with:
     "Look at the agent's recent calls (`list_calls`) for behaviour these rules do not
     settle, and raise each as a clarification."
   - **`get_spec` and `get_agent`** when the spec needs review (trigger 2) gain: "Raise
     what the change leaves unsettled, and replace (`replaces_key`) any answered rule it
     contradicts."
   - **`get_issue`** (trigger 3), when the issue's agent has a spec, gains: "If the
     spec does not say whether this behaviour is allowed, raise a clarification with
     these calls." (question 2)
   - **`get_spec`, `get_agent` and `get_readiness`** gain, when any are open: "7
     questions wait for the person on 2 agents: `list_clarifications`, then confirm the
     answers with them." Readiness's percentage does not change (question 3).
4. **`get_spec` data** gains `open_clarifications`, the agent's open count.
5. **`_SPEC_RULES`** gains: "Rules with source clarification are the person's answers:
   Connexity carries them into every version; never pass them to `write_spec`."

### The MCP server

- The three tools, their models and client calls are thin, as the other tools are.
- Their descriptions repeat the one rule that matters most for each tool, as
  `archive_issue` does.

## Decisions

- **Three tools, with park as an answer.** Proposed in part 1's plan and built that way
  in its service (rule 10: few tools).
- **A decision left to the assistant is an answer like any other.** Decided (Dmytro,
  2026-11-15: "on the backend it should be either answered or parked or open").
- **The triggers and where the assistant is told.** Decided (Dmytro, 2026-11-15: "Accept
  all three, add it to the plan").
- **No web routes yet.** The Action items page and its routes are part 3, after the
  demo.

## Questions

1. **No mark for "left to the assistant".** Recommend no flag: Dmytro said the backend
   knows only open, answered and parked. The assistant tells the person the answer is
   recorded as theirs. The alternative is a `delegated` flag on the answer, so the page
   can later say "decided by your assistant". It can be added later without changing
   the states.
2. **The `get_issue` next step** shows whenever the issue's agent has a spec, worded as
   "if". Recommend yes. The alternative is showing it only for some issue types, but
   Connexity cannot tell which issues are about unsettled behaviour without a model.
3. **Open questions add a Readiness next step, not a step or a percentage.** Recommend
   yes: answering is ongoing work, not setup.
4. **No "recommended answer" stored on a question.** For the batch, the assistant says
   in its session which it can answer confidently. Storing its suggestion belongs to
   the batch confirm flow after the demo. Recommend yes.

## Done when

- Through the MCP API on the local database, with an invented agent, spec and calls:
  1. `raise_clarifications` stores questions;
  2. `list_clarifications` shows them with their counts;
  3. `answer_clarifications` answers one and parks another;
  4. `get_spec` shows the new version with the answer's rule (source clarification) and
     the open count.
- A refused raise and a refused answer each answer 422 with every problem.
- Another workspace's agent or clarification answers 404 or "no clarification".
- `list_clarifications` filters by agent and state, and pages with `next_cursor`.
- The next steps above appear at each trigger, and the open-count step appears only when
  some are open.
- The spec guide, the server instructions and the tool descriptions say what is above.
  The MCP server tests cover the three tools.
- `make check` passes.

## Out of scope

- The Action items page, its sidebar count, answering in the app and its web routes
  (part 3).
- The batch confirm flow and stored suggested answers (after the demo).
- Connexity raising clarifications from calls (later).
- The Spec tab (Order 16.5).

## Risks

- **The assistant may answer without asking.** Connexity cannot check that the person
  confirmed. The rules, the tool description and the guide all say it; the decision
  record names the person and the assistant.
- **Too many questions.** The trigger next steps push the assistant to raise questions
  often. The guide asks for questions only about behaviour seen, or contradicted, and
  to check open ones first.

## Outcome

### Deviations from the plan

- **The getting-started guide** gains three sentences: questions the prompt does not
  settle are raised, confirmed with the person in one batch, and answered.
- **Review findings:**
  - an empty `answers` list now gets the standard refusal with next steps, not
    FastAPI's own 422 body (fixed);
  - `get_spec` counted the agent's open questions twice (fixed);
  - showing a replaced rule's current text reads each agent's latest spec, one agent at
    a time (left as it is: a page of 20 is small).

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

API play-through on the local server (`:8027`, local database). It used an invented
agent, prompt and two calls in a throwaway workspace, deleted afterwards:

| # | Request | Expected | Came back |
|---|---|---|---|
| 1 | `raise_clarifications` before any spec | 422, spec needed | 422; "The agent has no spec yet" |
| 2 | `write_spec` | 200, next step names `raise_clarifications` | 200; version 1, carried 0; it does |
| 3 | `raise_clarifications`, bad category and no answers | 422, every problem | 422; 2 problems listed |
| 4 | `raise_clarifications`, two questions (one with 2 calls, one with none) | 200 | 200; calls_seen 2 and 0; letters a, b, c |
| 5 | The same question again | 422 | 422; "already open or parked" |
| 6 | `list_clarifications` | 2 open | counts open 2, answered 0, parked 0; 2 items |
| 7 | `get_spec` | open count and waiting step | open_clarifications 2; step present |
| 8 | `get_readiness` | waiting step | "2 questions wait" present |
| 9 | `answer_clarifications` "B" and park | 1 answered, 1 parked, spec version 2 | answered 1, parked 1, open 0; version 2 with 1 rule added |
| 10 | Answering the same again | 422 | 422; "already answered (b)" |
| 11 | `get_spec` after the answer | version 2, origin answered, a clarification rule | version 2 answered; sources clarification and prompt; state current |
| 12 | `write_spec` passing the answered rule's key | 422 | 422; "a rule from the person's answer" |
| 13 | `write_spec` without it | 200, carried 1 | 200; carried 1 |
| 14 | `list_clarifications` parked, for the agent | 1, with who parked | 1 item; decided_by set |
| 15 | `list_clarifications` for an unknown agent | 404 | 404 |

The server log has no errors. The throwaway user, workspace and their rows were
deleted (0 left).

Tests:
- `app/tests/api/routes/test_mcp_clarifications.py`, 7 tests:
  - raise, list, answer and read the spec;
  - refusals;
  - another workspace;
  - filters and pages;
  - the `write_spec`, `get_agent` and `get_readiness` next steps;
  - `get_issue` with and without a spec;
  - an empty answer list.
- MCP server tests: the three tools, their annotations, the instructions line, and
  their client calls.

### Not done

- The Action items page: part 3, after the demo. When it merges, 10.12 is done.
- Reading a replaced rule's text with one query (see the review findings).
