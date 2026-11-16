# Session names

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Session names" (10.125). It builds on "Next
  task for the assistant" (10.124, #211, merged).
- **Design:** `designs/16-work.md` (the chip "assistant · session", the side panel's
  Session field) and `docs-internal/work.md` (Proposed: a named connection and named
  sessions). Screen: `designs/screens/Connexity Work.dc.html`. Nothing is built on
  screen here: the chip is drawn by the Work page (10.127).
- **MCP:**
  - `get_next_task` takes the session's name;
  - its answer says who holds each task in progress.

## Goal

One connection, such as Alex's Claude Code, can run several sessions at once, for
example "Onboarding" and "Car service booking". Each takes its own task through
`get_next_task`. Today Connexity tells assistants apart by the person and the assistant's
name only, so two sessions of one Claude Code share a single task. After this, each
session holds its own task, and Work can show "Alex's Claude Code · Onboarding".

## Decided in the roadmap row

These are Dmytro's words, 2026-11-16:
- **Sessions are their own feature** ("separate task").
- **The assistant names its session in its MCP calls,** and Connexity shows the name.
- **Key sessions by the MCP session id.** First check that the MCP adapter passes it
  through. Without it, the name is the key.
- **Shown on Work as the chip "assistant · session"** (10.127).

## What we found

- **No session id reaches Connexity.** The MCP adapter runs in stateless mode
  (`stateless_http=True` in `mcp_server/.../app.py`). It never hands out an
  `Mcp-Session-Id`, so clients send none. It forwards only the bearer token to the
  backend.
- **Turning sessions on is not a small switch.** Stateful mode keeps each session in
  the adapter's memory. On Cloud Run (`connexity-mcp`), requests can land on another
  instance, and a deploy drops every session. That would need session affinity and
  reconnect handling, and a dropped session would look like a new assistant.
- **So, as the row says, the name is the key** (question 1).

## Changes

### The session

- **`get_next_task(workspace_id, session)`:** `session` is a short name the assistant
  picks for this session ("Onboarding", "Car service booking"), from 1 to 40 characters.
  It uses the same name on every call in that session.
- **An assistant is the person, the assistant's name and the session name.** Two
  sessions of one Claude Code with different names hold different tasks. Two with the
  same name are one session and share a task.
- **Without `session`** it works as today: one unnamed session per assistant
  (question 3).

### The table

- **`assistant_task` gains `session_name`** (up to 40 characters, empty when none given),
  through migration `0025`. Ending and skipping use it as part of who holds the task.

### The answer

- **`get_next_task`'s answer gains `in_progress`:** the tasks other sessions hold, each
  with its title, the person, the assistant and the session. The assistant can then
  tell the person "Alex's Claude Code · Setup is connecting Slack" (question 4).
- **The count `in_progress_elsewhere` stays,** now counting other sessions of the same
  assistant too.

### Telling the assistant

- **The tool description and the getting-started guide's "What to do next":** "Name
  this session in a few words for the work it is on, such as `Onboarding`, and pass the
  same `session` on every `get_next_task` in it. Each session holds its own task."
- **A rule in the answer:** "Tasks are held per session: the person, the assistant and
  the session name."

## Decisions

- Everything under "Decided in the roadmap row" is Decided.
- No screen here; the chip is the Work page's (10.127).
- Everything under "Questions" is Proposed until Dmytro answers.

## Questions

1. **The name is the key, not a session id.** The adapter is stateless and Claude Code
   sends no session id to it. Recommend keying by the name now, as the row allows.
   Moving the adapter to stateful sessions is its own piece of work, with Cloud Run
   affinity and reconnects, and only worth it if names prove unreliable.
2. **Only `get_next_task` takes `session`.** Decisions (answers, archives, specs) keep
   recording the person and the assistant, as today. Recommend not adding `session` to
   every tool: tasks are where sessions matter, and fewer arguments keep the tools
   simple (rule 10).
3. **`session` optional.** Recommend optional: an assistant that leaves it out gets
   today's behaviour, and nothing breaks for one running a single session. The tool
   description and guide ask for it. The alternative, required, would refuse a call
   that leaves it out.
4. **`in_progress` in the answer.** Recommend listing what other sessions hold, up to
   10. The assistant can say who is on what, and Work later shows the same.
5. **The connection's name, "Alex's Claude Code".** The answer gives the person and the
   assistant separately (Alex, Claude Code); joining them into "Alex's Claude Code" is
   for the Work page. Recommend no stored connection name now.

## Done when

- **Through the MCP API** on the local database, with throwaway data:
  - two sessions of one assistant ("Onboarding", "Specs") each take a different task;
  - each sees the other's in `in_progress` with its session name;
  - asking again in one session ends only that session's task;
  - a call without `session` behaves as before.
- **`make check` passes.**

## Out of scope

- The Work page and its chip (10.127).
- MCP session ids and a stateful adapter (question 1).
- Blocks and Blocked by (10.126).

## Risks

- **Names are chosen by the assistant.** Two sessions that pick the same name share a
  task, and a session that changes its name looks like a new one. Its old task then
  stays In progress until its work is done. The guide asks for one name per session,
  kept for the whole session.

## Outcome

### Deviations from the plan

- **Tasks in `in_progress` carry their position** in the list (a review finding, fixed).
- **Review findings left as they are:**
  - a session that renames itself leaves its earlier task In progress under the old
    name until that work is done (the risk above);
  - each held task looks up its person separately.

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

Tests ran with `TEST_DATABASE_URL` pointing at the local container (its password
differs from `.env`).

**Migration:** `0025_assistant_task_session` runs up, down and up again on the local
database, and `alembic check` finds no drift. The local database was then put back on
main's `0023`.

**MCP play-through** on the local server (`:8027`, local database). One OAuth client was
named as one assistant, Claude Code. The throwaway workspace was the one from 10.124: a
Critical issue, an agent without a spec, an open question, and the first scan not done.
Everything was deleted afterwards:

| # | Request | Expected | Came back |
|---|---|---|---|
| 1 | `get_next_task`, session "Onboarding" | the top task | 200; issue_fix #1; 0 in progress elsewhere |
| 2 | Same assistant, session "Specs" | a different task; sees Onboarding's | 200; onboarding #3; in_progress: Claude Code · Onboarding |
| 3 | "Specs" asks again | only its own task ends | 200; previous returned; now onboarding #4; Onboarding still holds its task |
| 4 | Same assistant, no session | behaves as before, as one more session | 200; onboarding #3; in_progress: Onboarding, Specs |
| 5 | A 41-character session name | refused | 422 |

The server log has no errors.

Tests:
- `test_next_task.py` gains two tests: each session of one assistant holds its own task
  and ends only its own, and the session through MCP, with `in_progress` and the length
  limit;
- the MCP client test checks that `session` is passed through.

There is nothing to check on screen.

### Not done

- The chip "assistant · session" on Work (10.127).
- MCP session ids and a stateful adapter (question 1).
