# Deleting a workspace's data

An agency can remove a client workspace and everything Connexity holds about its calls,
for good. Plan: [`plans/2026-11-24-delete-workspace-data.md`](../plans/2026-11-24-delete-workspace-data.md).
The code is `app/crud/workspace_deletion.py` and `app/api/routes/workspace_deletions.py`.
The screens (Agency settings › Workspaces) come with the second pull request of the
roadmap row.

## What is removed and what stays

Removed: every row of every table that carries the workspace's `company_id`: calls with
their transcripts, tool calls, findings and checks, issues, clarifications, decision
records, specs, scenarios, test runs and results, tasks, connections with their stored
keys, ingest tokens and feedback reports. Connexity stores no audio, only the voice
platform's link to a recording, so nothing lives outside the database. Nothing is called
on the voice platform, n8n or a CRM: the agency's calls there are not touched.

Three kinds of row stay, with no call content:

| Row | What is left of it | Why |
|---|---|---|
| `usage_record` | Units, meter, time, own cost; links to the call, run and result emptied | Invoices |
| `company` and `agent` | Id and name, `deleted_at` set; an agent's platform ids, connection, metadata and scan state emptied | Kept usage still says whose it was (Decided by Dmytro, 2026-11-24) |
| `workspace_deletion` | Who deleted which workspace and when, its state, and how many calls, agents and issues it held | The agency's record of the decision |

`KEPT_TABLES` in the code is the whole list. Every other table with a `company_id` is
emptied, in the reverse of the order the tables depend on each other, so a table added
later is covered without a change here. A test fails when a table that is not emptied
points at one that is without saying what happens on delete.

## How a deletion runs

1. The record is written, the workspace gets `deleted_at`, every person's access row
   for it is removed, and its agents are unlinked from their connection (so the webhook
   and the call pull store no new call), in one commit. From here nobody reaches it, on the web or through
   an assistant, whatever happens next. People who had it open are moved to another
   workspace they reach; with none left they meet the "no workspace" sign-in refusal.
2. Usage rows lose their links; agents are reduced to id and name; an assistant's
   connection made while this workspace was open moves to the workspace its person has
   open now.
3. Each table is emptied and committed in turn.
4. The record becomes `done` and the agency's Admins get an email.

It runs inside the request that asks for it. A step that breaks leaves the record
`failed`, with the step and the kind of error (never the error's text, which can quote a
row). "Try again" runs the same steps again; they are safe to repeat.

## Rules

- **Who:** an Admin of the agency who can approve. Others are refused and told who can.
- **Confirmation:** the workspace's name, typed exactly.
- **The last workspace** of an agency cannot be deleted (Decided by Dmytro, 2026-11-24):
  every account needs an open workspace. The refusal says to create another first.
- **No assistant can delete.** The routes take a web session only, and there is no MCP
  tool that deletes.
- **Backups** of the hosted database are outside the app; nothing here promises when
  they forget a deleted workspace.

## Routes

| Route | Who | What |
|---|---|---|
| `GET /api/v1/agencies/{id}/workspaces` | Anyone in the agency | The workspaces with agents and calls stored, `can_delete`, and the record of deleted ones |
| `GET /api/v1/agencies/{id}/workspaces/{workspace_id}/deletion` | Admin who can approve | What a deletion would remove; deletes nothing |
| `POST /api/v1/agencies/{id}/workspaces/{workspace_id}/deletion` | Admin who can approve | Deletes; the body carries the typed name |
| `POST /api/v1/agencies/{id}/workspaces/{workspace_id}/deletion/retry` | Admin who can approve | Continues a failed deletion |
