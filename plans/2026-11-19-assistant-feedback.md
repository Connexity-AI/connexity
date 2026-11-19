# The assistant reports bugs and feature requests

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "The assistant reports bugs and feature
  requests" (10.1995).
- **Design:** No UI change.
- **MCP:** a new tool, `send_feedback` (writes), with its `contract.py` entry and a
  description for every input; a new guide, `connexity://guides/feedback`; one sentence
  in the server instructions.

## Goal

Dmytro, 2026-11-19: an MCP way for the assistant to report Connexity's own bugs and
feature requests, so he hears what breaks and what is missing from the assistants that
use it. After this merges, an assistant that knows nothing about how Connexity is built
reports a failing tool clearly (the tool, the error, the ids) without asking the person,
and the report appears as a New row in the "Assistant feedback" Notion database.

## Decisions

### Decided by Dmytro (2026-11-19, the roadmap row)

- The backend posts each report to Notion, to its own page ("Can we post it from backend
  to Notion separate page"). The "Assistant feedback" database already exists, with
  Title, Kind (Bug, Feature request), Status (New, Triaged, On roadmap, Won't do, Fixed),
  What happened, Wanted, Tool, Error, IDs, Workspace, Sent by, Assistant, Connexity
  version, Report ID, Received and Roadmap. Its id lives in an environment variable,
  never in the repo.

### Decided while planning (Dmytro, 2026-11-19)

- Dmytro runs the fresh-assistant test himself after merge; this PR tests through the
  API.
- At most **20 reports a day** per workspace; past that the tool refuses politely and
  says to try tomorrow.
- A report Notion did not accept is retried on the scheduled call pull's tick, **at most
  5 tries**; then it stays stored with its last error.

### Proposed (in the row, carried here)

- One tool, `send_feedback`, never failing because Notion is down.
- The report is stored first and posted to Notion after; without the Notion settings
  (local runs, self-hosting) reports are only stored.
- A dedicated Notion integration shared with that one database only, not the roadmap's
  key.

## Changes

### `send_feedback`

- **Inputs:**
  - `kind`: `bug` or `feature_request`;
  - `title`: one line;
  - `what_happened`: for a bug, what the assistant did, which tool, what it expected and
    what came back;
  - `wanted`: for a request, what the work needed and could not do;
  - `tool`: the Connexity tool involved, optional;
  - `error`: the answer's text, optional;
  - `ids`: the call, issue, run, agent or task ids involved, optional.
- **The answer:** the report's id, that the Connexity team reads every report, and a
  next step to tell the person in one sentence that it was reported, then carry on.
- **Rules in the answer:** never put caller data in a report (no transcripts, phone
  numbers or names); describe what happened and give ids instead. Never put secrets.
  One report per problem.
- **Refusals:** an empty title, or a bug without `what_happened` (or a request without
  `wanted`), is refused with what is missing. More than 20 reports in a day from one
  workspace is refused politely, saying to try tomorrow.
- Each text input has a length cap; `error` is cut, not refused, so a long error still
  goes through.

### When the assistant uses it

- **Server instructions** gain one sentence: when a Connexity tool fails, contradicts
  another answer, or cannot do what the work needs, report it with `send_feedback`,
  after one retry, without asking the person, then tell them in a sentence.
- **The tool's description** and **the guide** (`connexity://guides/feedback`) say the
  same, with what makes a good report and what it is not for: problems in the person's
  own agent are issues, not feedback.
- **Error answers** from Connexity's tools (the `McpErrorDetail` that every refusal and
  failure carries) end with a next step naming `send_feedback` when the error is
  Connexity's own (a 5xx or an unexpected failure), not when the assistant sent
  something wrong. Proposed: so an assistant that never read the guide still finds it.

### Storing and posting

- **A table, `feedback_report`** (migration), per workspace: kind, title, what
  happened, wanted, tool, error, ids, the person, the assistant's name, the session's
  name, the Connexity version, when it was received, and when it reached Notion (its
  page id), with the last error if it did not.
- **Posting:** right after storing, in the background; if Notion fails, the report stays
  unsent and the scheduled call pull (`/internal/calls/pull`, every few minutes)
  retries unsent reports, at most 5 tries each.
- **The Notion row:** Title, Kind, Status New, the texts, Tool, Error, IDs, Workspace
  (its name), Sent by (the person's name or email), Assistant (name and session),
  Connexity version, Report ID, Received.
- **The Connexity version** is the Cloud Run revision (`K_REVISION`), or "local".
- **Settings:** `NOTION_FEEDBACK_TOKEN` and `NOTION_FEEDBACK_DATABASE_ID`, optional, in
  `.env.example` and in `deployment.md` as Cloud Run secrets. Dmytro creates the
  integration and adds the secrets (cloud settings are his).

## Done when

- Route tests through the API (local database), with Notion mocked (`respx`):
  - `send_feedback` stores a report and posts it, with the right properties, and answers
    its id;
  - Notion failing (timeout, error, malformed answer) still answers the report's id;
    the report stays unsent and the next pull tick sends it;
  - without the Notion settings, the report is stored and nothing is posted;
  - missing fields and the daily cap are refused;
  - another workspace cannot report into this one.
- The MCP adapter test sends every input; the contract test passes with the new tool
  and its descriptions.
- After merge, Dmytro's own test with a fresh assistant: a clear bug with the tool, the
  error and the ids, a New row in the Notion database.

## Out of scope

- Reading reports back through MCP or in the web app.
- Telling the person or the assistant when a report is triaged or fixed.
- Moving reports to the roadmap automatically (Dmytro triages by hand).

## Risks

- An assistant may put caller data in a report despite the rules. The rules say no, and
  Dmytro's Notion is private; there is no filter on the text.
- The Notion token is a write key: it is a secret, never logged.

## Outcome

### Deviations from the plan

- **Connexity's own failures point to `send_feedback` in the MCP adapter,** not in each
  backend error answer. Any 5xx or failed request to the backend gets one sentence: it
  is a problem in Connexity, retry once, then report it. That covers every tool,
  including unexpected crashes, whose answer the backend cannot shape. `send_feedback`'s
  own failure does not get it.
- **A report is taken by one post at a time** (`claimed_at`), so the request's
  background post and a scheduled tick never post it twice. A post that never finished
  can be taken again after two minutes.
- **A tick posts at most 10 reports,** so a Notion outage cannot hold up the call pull.
- **The cap counts the last 24 hours;** the refusal says to send it later.
- **An error is kept up to 10,000 characters,** and cut to 2,000 in Notion.
- **The answer has no "posted" flag.** The post happens after the answer, so the
  answer only gives the report's id.

### Check results

`make check`, run before the pull request: every step ok except "Generated client is
fresh", which regenerated the client for the new route. Rerun after that: fresh.
Frontend types ok on the regenerated client.

No separate play-through server: the route tests send the same requests through the API
(`TestClient` on the local database), with Notion mocked (`respx`):
- a report is stored with its kind, tool, ids, session, person and version, and
  answered with its id and the rules. Without the Notion settings nothing is posted;
- a stored report reaches Notion as a New row with every property, its page id is
  kept, and it is not posted again;
- Notion refusing, timing out, or answering nonsense or without a page id keeps the
  report, counts its tries up to 5 and keeps the last error;
- a missing title, a bug without `what_happened` and a request without `wanted` are
  refused, and nothing is stored;
- the daily cap refuses the next report;
- a long error is cut for Notion, and another workspace cannot be reported into;
- a report is taken by one post at a time;
- the MCP adapter sends every input without empty ones, a Connexity failure points to
  `send_feedback`, and the contract and server tests list the new tool and group.

No UI change, so nothing to check on screen.

### Not done

- The fresh-assistant test runs after merge, by Dmytro (Decided).
- The Notion integration and its two Cloud Run secrets are Dmytro's to add. Until then,
  reports in production are stored and not posted.
