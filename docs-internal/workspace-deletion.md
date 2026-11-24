# Deleting a workspace's data

An agency can remove a client workspace and everything Connexity holds about its calls,
for good. Plan: [`plans/2026-11-24-delete-workspace-data.md`](../plans/2026-11-24-delete-workspace-data.md).
and [`plans/2026-11-24-delete-workspace-screens.md`](../plans/2026-11-24-delete-workspace-screens.md).
The code is `app/crud/workspace_deletion.py` and `app/api/routes/workspace_deletions.py`;
the screen is `frontend/apps/web/src/components/agency/workspaces-view.tsx`.

## What is removed and what stays

Removed: every row of every table that carries the workspace's `company_id`: calls with
their transcripts, tool calls, findings and checks, issues, clarifications, decision
records, specs, scenarios, test runs and results, tasks, connections with their stored
keys, ingest tokens and feedback reports. Connexity stores no audio, only the voice
platform's link to a recording, so nothing lives outside the database. Nothing is called
on the voice platform, n8n or a CRM: the agency's calls there are not touched.

Four kinds of row stay, with no call content:

| Row | What is left of it | Why |
|---|---|---|
| `usage_record` | Units, meter, time, own cost; links to the call, run and result emptied | Invoices |
| `oauth_refresh_token` | An assistant's connection: moved to the workspace its person has open, or left as it is when they reach no other | The assistant stays connected, and reaches nothing until its person has a workspace again |
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
row). "Try again" runs the same steps again; they are safe to repeat. A deletion still
marked as running after five minutes belongs to a request that died; it counts as failed
and can be tried again the same way.

## Rules

- **Who:** an Admin of the agency who can approve. Others are refused and told who can.
- **Confirmation:** the workspace's name, typed exactly.
- **The last workspace** of an agency is deleted like any other (Decided by Dmytro,
  2026-11-24, replacing the earlier rule that it could not be). The dialog adds that it
  is the last one and that the subscription keeps running until it is cancelled. Its
  Admins then have no workspace open: see "With no workspace" in
  [`agency.md`](./agency.md).
- **No assistant can delete.** The routes take a web session only, and there is no MCP
  tool that deletes; `prepare_workspace_deletion` only reads.
- **Backups** of the hosted database are outside the app; nothing here promises when
  they forget a deleted workspace.

## Screens

Agency settings › Workspaces (`/agency?section=workspaces`,
`designs/screens/Connexity Workspaces.dc.html`): the table, the "⋯" menu for a person
who can delete, the dialog with the typed name, the Record list. Where the build differs
from the design:

- **The line while deleting has no percentage.** A deletion runs inside one request, so
  there is none to show; the line pulses while the request runs.
- **The connection line names the platforms the workspace is connected to,** and is
  left out when it has none.

## A session in a deleted workspace

A web session names the workspace it was opened in and normally ends when its person
loses that workspace. A deletion is not a change to the person's access, so the session
goes on when they reach another workspace (`_is_member` in `app/api/deps.py`). The app
layout sees that the session's workspace is no longer in the person's list and shows the
full page "This workspace is being deleted." with a link that opens another workspace
(`components/shell/workspace-deleted.tsx`). A person who reaches no other workspace is
refused, as before. The person who deleted gets a session in their open workspace right
away, so they stay on the Workspaces table.

## The assistant

`prepare_workspace_deletion(workspace_id)` answers what a deletion would remove, whether
the assistant's person can delete it, who can, whether it is the agency's last
workspace, and the address of the Workspaces section. It deletes nothing, and no tool
deletes. After a deletion every tool answers "not found" for that workspace.

## Routes

| Route | Who | What |
|---|---|---|
| `GET /api/v1/agencies/{id}/workspaces` | Anyone in the agency | The workspaces with agents and calls stored, `can_delete`, and the record of deleted ones |
| `GET /api/v1/agencies/{id}/workspaces/{workspace_id}/deletion` | Admin who can approve | What a deletion would remove; deletes nothing |
| `POST /api/v1/agencies/{id}/workspaces/{workspace_id}/deletion` | Admin who can approve | Deletes; the body carries the typed name |
| `POST /api/v1/agencies/{id}/workspaces/{workspace_id}/deletion/retry` | Admin who can approve | Continues a failed deletion |
