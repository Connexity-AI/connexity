# Delete workspace data (1 of 2): the deletion, its record and the assistant tool

- **Owner:** Dmytro
- **Slice:** Delete workspace data (roadmap Order 102.38), first of two pull requests.
  The second brings the screens, after Dmytro hands over the design export.
- **Design:** the Claude Design prompt in the roadmap row (2026-11-23). **The screens
  are not designed yet:** no page in `designs/screens/` or in the last export shows the
  Workspaces section, the delete dialog or the email. Screens are built only after
  Dmytro hands over the export.
- **MCP:** no tool changes in this pull request. The planned tool that prepares a
  deletion moves to the second pull request, with the screen it points to (see Outcome).
- **Status:** Approved by Dmytro ("approve", 2026-11-24).

## Goal

An agency can permanently remove a client workspace and everything Connexity holds about
its calls, and can show afterwards who removed it and when. Usage totals needed for
invoices stay, with no call content.

## What the code is today

- **Nothing can be deleted:** there is no code that deletes a workspace, an agent or a
  call. About 25 tables carry `company_id`, almost all without a delete rule.
- **Connexity stores no audio:** a call holds the voice platform's `recording_url`, the
  transcript, tool calls and findings. Deleting is database work only; nothing has to be
  removed from file storage.
- **Decision records belong to a workspace** (`decision_record.company_id`), so the
  record of a deletion cannot live there: it would be deleted with the workspace.
- **Usage rows point at the workspace and the agent** (`usage_record.company_id`,
  `agent_id`), and hold units, a source key such as `call:<id>`, and Connexity's own
  cost. No transcript or caller data.
- **Every account has an open workspace** (`user.company_id` is required), and sign-in
  refuses a person who reaches no workspace.

## Changes

### Backend

- **A deletion record at the agency level:** new table `workspace_deletion` (agency,
  workspace id and name, who, when asked, when finished, state `deleting`, `done` or
  `failed`, and the counts shown in the dialog). It holds no call content and is the
  permanent record of the decision.
- **The workspace row stays as a tombstone:** `company.deleted_at` is set and the name
  kept, so usage totals still say which client they were for. A deleted workspace is
  gone from every list, picker, route and assistant tool at once.
- **Deleting runs in steps, in an order that can be repeated:** connections first (so no
  new calls arrive; nothing is called on the voice platform), then calls with
  transcripts, tool calls, findings and checks, then issues, clarifications, decision
  records, specs, scenarios, test runs and results, tasks, tokens, then agents. A failed
  run keeps state `failed` and "Try again" continues where it stopped.
- **Usage rows stay,** with `call_id`, run and result links emptied. So that totals
  still name the agent, each agent's row stays as a tombstone too: its id and name, with
  its prompt, configuration and platform ids emptied.
- **The last workspace of an agency cannot be deleted:** the refusal says to create
  another workspace first.
- **Routes** under `/agencies/{id}/workspaces`: the table (agents, calls stored,
  created, deletion state), a preview of what a deletion removes, start a deletion (the
  workspace name typed must match), try again.
- **Who:** an Admin of the agency who can approve. Anyone else gets a refusal naming
  who can.
- **Email** to the agency's Admins when a deletion finishes, in the layout of the reset
  and invite emails.
- **People with the deleted workspace open** are moved to another workspace they reach;
  with none left they meet the existing "no workspace" refusal.

### Assistants

- **`prepare_workspace_deletion(workspace_id)`:** answers what would be deleted (the
  dialog's counts), who can do it, and the link to Agency settings › Workspaces. It
  deletes nothing. There is no tool that deletes.
- **Every other tool** answers "this workspace was deleted" for a deleted workspace.

### Frontend

- None in this pull request. The second one builds Agency settings › Workspaces, the
  delete dialog, the deleting and failed row and the full-page line for people inside a
  workspace being deleted, from the design export.

### Docs

- New `docs-internal/workspace-deletion.md`; `data-model.md`, `agency.md`,
  `mcp-architecture.md`, `decisions.md`.

## Decisions

- **Decided (roadmap row, Dmytro 2026-11-23):** deleting removes calls, recordings,
  transcripts and everything derived; usage records for invoices stay without call
  content; it needs a person's approval and cannot be undone; the assistant can prepare
  it and the person approves.
- **Proposed:** the person deleting is an Admin who can approve (from the design
  prompt).
- **Proposed:** the workspace row stays as a tombstone with its name.
- **Decided (Dmytro, 2026-11-24):** backend first, screens in a second pull request
  after the design.
- **Decided (Dmytro, 2026-11-24):** kept usage rows still say the workspace's and the
  agent's name; no call, transcript or caller data stays.
- **Decided (Dmytro, 2026-11-24):** deleting an agency's last workspace is refused for
  now. The designed empty state "No workspaces yet" needs the app to work with no open
  workspace and becomes its own roadmap row.
- **Proposed:** an agent's row stays as a tombstone with only its id and name, which is
  how usage keeps the agent's name.

## Done when

- Through the API on the local database: after a deletion no call, transcript, finding,
  issue, spec, scenario, test run or agent of the workspace can be read by any route or
  assistant tool, another workspace of the same agency is untouched, usage totals for
  the period are unchanged, and the deletion record names who and when.
- A Member, an Admin who cannot approve and an assistant are refused.
- A deletion that fails halfway can be tried again and finishes.
- The email reaches every Admin once.

## Out of scope

- The screens (second pull request) and the empty state after the last workspace (its
  own row, to be added by the Roadmap session when Dmytro says so).
- Deleting single calls, a single agent or an agency; deleting a person's account.
- Removing anything on the voice platform, n8n or a CRM.
- Database backups: what the hosted database's own backups keep, and for how long, is
  outside the app. The Terms and privacy pages should say so; nothing here promises it.

## Risks

- **A very large workspace could outlast the request.** Each table is committed on its
  own and "Try again" continues, so nothing is left half-known; moving the run to the
  background is the fix when volumes call for it.

- **A wrong deletion cannot be undone.** The typed name, the approve rule and the tests
  that another workspace is untouched are the guard.
- **Tables added later** must join the deletion. A test fails when a table with
  `company_id` is not handled.

## Outcome

### Deviations from the plan

- **The assistant tool `prepare_workspace_deletion` is not in this pull request.** It
  answers "the person deletes it in Agency settings › Workspaces", and that screen
  arrives with the second pull request. A tool pointing at a screen that is not there
  would break the rule that nothing is offered that does not work end to end, so the
  tool, its contract entry and guide move to the second pull request. No MCP tool
  changed here. For a deleted workspace every existing tool already answers "not
  found", because nobody reaches it any more; that is tested.
- **The deletion runs inside the request,** not in the background. The hosted database
  holds one workspace with about a hundred calls, so a deletion takes well under a
  second; a background run on Cloud Run can be paused after the answer is sent and
  would then hang in "deleting". The states `deleting`, `done` and `failed` and "Try
  again" are built as planned, each table is committed on its own, and the run can be
  moved to the background later without changing the routes.
- **An assistant's OAuth connection made while the deleted workspace was open moves**
  to the workspace its person has open now, instead of being removed. Removing it
  would disconnect the assistant from the person's other workspaces.
- **A failed deletion's record keeps the step and the kind of error only,** not the
  error's text, which can quote a row.
- **"Connections first" became "agents unlinked first":** a connection row cannot go
  before the calls that point at it, so the first commit unlinks the agents instead,
  which is what stops new calls. The connection's stored key goes a moment later.
- **Tables are found, not listed:** every table with a `company_id` is emptied unless it
  is one of the four kept ones, so the plan's list of steps is not spelled out in code.
- **People who had the deleted workspace open are signed out of that session** (their
  session names the workspace) and land in another workspace when they sign in again.
  The designed full-page line "This workspace is being deleted." is the second pull
  request's.

### Check results

Route tests through the API on the local database (`TestClient`; no separate
play-through server, the tests send the same requests as a web session and as an
assistant with a personal access token):

| What | Result |
|---|---|
| `test_workspace_deletion.py` (6 tests): after a deletion only the usage row, the agent's row and the record are left for the workspace, with the agent reduced to its name and usage keeping its units; another workspace of the same agency is unchanged; the Admins get the email once; the workspace is gone from the web list, the assistant's list and tools, and the agency's table, whose record says who and how much; a Member who can approve, an Admin who cannot, an outsider and an assistant are refused, and a wrong name is refused; the last workspace is refused; a deletion that breaks on calls is `failed` with the step named, stays unreachable, and finishes on "Try again"; a table that is not emptied may not point at one that is without a delete rule | passed |
| Agency and invite tests (29), schema matches the migration, email tests | passed |
| Backend `ruff` and `pyright`; generated client regenerated; frontend types | passed |
| Full `make check`, after the review fixes | every code step passed; the plan step failed on a heading ("Changes (Proposed)"), which was corrected and the plan check run again: passed |

### Code review

Two findings, both fixed:

- A deletion that failed in its first steps left the workspace's agents connected, so
  new calls would still be stored and checked in a workspace nobody reaches. Agents are
  now unlinked from their connection in the same first commit that takes the workspace
  away.
- Two delete requests for one workspace at the same moment answered the second with a
  server error. It now gets the "already deleted" refusal.

One thing to know, not a defect: feedback reports sent from the workspace
(`feedback_report`) are deleted with it, because they can quote what happened on a call.
What was already forwarded to Connexity's team at the time it was sent is not recalled.

### Not done

- The screens, the assistant tool and the full-page line (second pull request, after the
  design export).
- No deletion email was sent through the real provider; sending is tested up to the
  hand-over to SMTP, with the subject and sentence checked.
- Nothing was deleted in the hosted database. It was read once, read only, for row
  counts per table.
- Large workspaces: a deletion of tens of thousands of calls inside one request is not
  measured. See Risks.
