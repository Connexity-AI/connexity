# Bulk read of calls for the assistant

- **Owner:** Dmytro
- **Slice:** Bulk read of calls for the assistant (roadmap Order 102.56), one pull
  request.
- **Design:** none. No screen changes: this is a read for assistants only.
- **MCP:** a new tool, `read_calls`, that returns many calls with their transcripts and
  tool calls. Contract entry, a description for every input,
  guide text and tests come with it.
- **Status:** Approved by Dmytro ("Accept, build", 2026-11-24).

## Goal

An assistant that wants to measure a pattern across a period's calls reads them in a
few requests instead of one request per call, and does its own analysis on what it
read: what was said, which tools were called, with which arguments and results.

## What the code is today

- **`list_calls`** answers a page of calls with their filters (agent, result, category,
  period, issue, version, search by phone number or call id), without what was said.
- **`get_call`** answers one call in full: every turn, every tool call with its
  arguments and result, the findings. Forty calls are forty requests (assistant
  feedback, 2026-11-20).
- **Sizes, measured on the hosted database** (109 calls, sizes only): a call has 18
  events on average and 67 at most; stored, its events are about 8,000 characters on
  average, 15,500 for the largest tenth and 29,500 at most.
- **Assistant apps cap a tool's answer.** A common limit is about 25,000 tokens, which
  is roughly 100,000 characters.

## Changes

### Assistants

- **`read_calls` answers a page of calls in full,** using exactly `list_calls`' filters, so
  the same question that lists calls can read them.
- **Each call, compact:** its id, agent, start, length, version, result, the caller's
  last four digits, the findings by title, and the conversation in order: who spoke
  and what was said, and each tool call with its name, arguments and result. No
  timings, no recording link, no raw platform payload.
- **Sized to fit:** a page stops at 50 calls or when it reaches about 60,000
  characters, whichever comes first, and answers a cursor for the rest. A single call
  larger than that is answered alone, whole. At the measured sizes that is about 10 to
  15 calls a page, so 40 calls take three or four requests.
- **The same protections as `get_call`:** secrets in tool arguments and results are
  masked, callers show as their last four digits, and only the workspace the person
  reaches is read.
- **Rules in the answer:** the assistant does its own analysis on what it read;
  Connexity filters only on what it owns (issues, findings, versions, results,
  categories, period), and a pattern worth watching on every call becomes a check.

### Backend

- One route, `GET /api/v1/mcp/workspaces/{workspace_id}/calls/read`, reading calls and their
  events in a fixed number of queries per page, not one set per call.

### Docs

- `docs-internal/mcp-architecture.md`, the calls guide, the `/mcp-docs` contract entry.

## Decisions

- **Decided (Dmytro, 2026-11-20, roadmap row):** Connexity filters only on what it owns;
  no filters by tool or argument; custom searches are the assistant's own analysis over
  a bulk read; no "reveal number".
- **Proposed:** the compact shape above, and the page limits (50 calls, about 60,000
  characters).
- **Decided (Dmytro, 2026-11-24):** a new tool, `read_calls`. `list_calls` keeps
  answering a light list.

## Done when

- Through the API on the local database: a page answers each call's turns and tool
  calls in order with arguments and results; every `list_calls` filter narrows it the
  same way; a page stops at the size limit and its cursor continues without a gap or a
  repeat; a call larger than the limit comes alone and whole; a secret in a tool
  argument is masked; another workspace's calls are never answered.
- MCP server tests pass with the tool, its inputs' descriptions and the contract entry.
- The full `make check` passes.

## Out of scope

- Filters by tool name, argument or free text in transcripts (decided against).
- Simulated calls from test runs: `get_test_runs` already answers those.
- Any screen.

## Risks

- **An answer too large for the assistant's app is lost whole.** The size limit is set
  well under the common cap, and is one constant.
- **Reading many transcripts is reading client data in bulk.** It is the same data
  `get_call` already answers, to the same person, with the same masking.

## Outcome

### Deviations from the plan

- **Each call is built by the single call's own code,** not by a fixed number of
  queries per page as the plan said. That code already decides what a call's
  conversation is and masks secrets; reusing it means `read_calls` and `get_call` can
  never disagree. It costs a handful of queries per call, on pages of 10 to 15 calls.
- **Empty fields are left out of each turn** (a spoken turn has no `tool`, a tool call
  no `speaker`), so the page holds more calls. The rest of the answer keeps every
  field, as other tools do.
- **`matching`:** the answer also says how many calls the filters match, so the
  assistant knows how much is left to read.
- **A call with no transcript yet** is answered with an empty conversation, not left
  out, so the count and the paging stay true.

### Check results

Route tests through the API on the local database (`TestClient`; no separate
play-through server):

| What | Result |
|---|---|
| `test_read_calls.py` (8 tests): a page answers each call's turns and tool calls in order with arguments and results, newest first, compact, with secrets masked and the caller as four digits; every `list_calls` filter narrows it to exactly what `list_calls` lists; a page stops at the size limit and its cursor goes on without a gap or a repeat; a call larger than the limit comes alone and whole; the count is capped at 50 and nothing matching says so; another workspace's calls are never read; the single-call route still answers by id; the same number of characters in Chinese fills a page sooner than in English | passed |
| Single-call and call-list tests | passed |
| MCP server tests (71), with the tool, its inputs' descriptions and the contract entry | passed |
| Backend `ruff` and `pyright`; generated client regenerated | passed |
| Full `make check`, after the review fix | passed, every step |

### Code review

Two findings:

- **Fixed:** the page limit counted characters, but assistants count tokens, and a
  character of Chinese or Cyrillic costs several times an English letter. A page of
  such transcripts could be far larger than an assistant's app accepts. The limit is
  now 60,000 bytes, which grows with those scripts. Tested.
- **Left, and it was there before:** when a call arrives between two pages, the next
  page repeats one call. Nothing is skipped. `list_calls` pages the same way; paging
  from a call's start time instead would fix both and is a wider change. The guide
  does not promise otherwise.

### Not done

- **Not tried with a real assistant.** The page limit (60,000 bytes, about 60,000 characters of English) is set
  from measured call sizes and the cap assistant apps commonly have; whether a page
  reads comfortably in one is seen the first time an assistant uses it.
- **Simulated calls** are not part of it; `get_test_runs` answers those.
