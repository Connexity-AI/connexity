# Agency account

- **Owner:** Dmytro
- **Slice:** Agency account (roadmap Order 102.35)
- **Design:** No UI change in this pull request. The screens that show agencies and
  people (Members, invites, the profile menu with several agencies, Settings › Team) are
  the roadmap row "Invites and Members screen" and its design prompt.
- **MCP:** `list_workspaces` says which agency each workspace belongs to, the person's
  role there and whether they can approve. `create_workspace` takes the agency to
  create in (needed only when the person is an Admin of more than one). Both get their
  `contract.py` entries, a description for every input, and the `workspaces` guide.

## Goal

An agency is one account above its client workspaces. It owns the people and, later,
the billing. After this merges every workspace belongs to an agency, every person has a
role in it, the workspaces they can reach and whether they can approve, and an assistant
reaches exactly its person's workspaces.

Today a workspace stands alone: a person reaches it through one membership row, there
are no roles, and nothing can hold a balance for several workspaces. Billing (the next
rows) needs the agency to exist first.

Nothing a person sees changes with this pull request.

## Changes

### Data

- **New table `agency`:** a name and when it was made.
- **`company.agency_id`:** every workspace belongs to exactly one agency.
- **New table `agency_member`:** one row per person in an agency, with
  - `role`: `admin` or `member`;
  - `all_workspaces`: whether the person reaches every workspace of the agency,
    including ones created later;
  - `can_approve`: whether the person may make the critical decisions in their
    workspaces.
- **`workspace_member` stays** as the list of chosen workspaces for a person whose
  `all_workspaces` is off.
- **Migration of what exists:** workspaces that share a person become one agency (so a
  person with three client workspaces gets one agency, not three). Everyone in it
  becomes an Admin who can approve; a person who was a member of every workspace in it
  gets "all workspaces", anyone else keeps exactly the workspaces they had. Checked on
  the hosted database (2026-11-23, counts only): 2 workspaces, 1 person, 2 memberships,
  so production becomes one agency with one Admin.

### Access (one rule, in `app/crud/workspace.py`)

A person reaches a workspace when they are in its agency and either have "all
workspaces" or have that workspace chosen. The web session check, the web routes, every
MCP route, personal access tokens and OAuth connections already go through this module,
so they all follow the new rule with no change of their own.

### What changes for people and assistants

- **Sign-up** (web, Google, and the account form where an assistant connects) creates an
  agency, named like the first workspace is today (from the email's domain), with the
  person as its Admin, all workspaces, can approve. Then the first workspace, as today.
- **Creating a workspace** (web and `create_workspace`) creates it in an agency. It is
  refused for a person who is not an Admin of that agency.
- **Agency routes for the next row's screens,** tested here through the API:
  read an agency and its people; rename it; change a person's role, workspaces and
  "can approve"; remove a person. All but reading are for Admins.
- **Guard rails:** the last Admin cannot be removed or made a Member (409). A person
  removed from an agency loses its workspaces at once, on the web and for their
  assistants; if the workspace they had open was one of them, another they can reach is
  opened, and with none left they are sent to sign-in with a plain message.
- **`list_workspaces`** adds, per workspace, the agency (`id`, `name`), the person's
  `role` and `can_approve`.

### Docs

- `docs-internal/`: a new `agency.md` (the model, the access rule, the guard rails),
  `data-model.md`, `mcp-architecture.md`, `decisions.md`. `docs/` where workspaces are
  described for people outside.

## Decisions

1. **Decided (Dmytro, 2026-11-12 and the roadmap row, 2026-11-23):** a thin agency
   account above client workspaces that owns members and billing; clients never log in;
   Admin and Member roles; a person can belong to more than one agency; an agency always
   keeps at least one Admin; each person has the workspaces they can reach (all or
   chosen) and whether they can approve; assistants reach exactly their person's
   workspaces.
2. **Proposed:** "all workspaces" includes workspaces created later.
3. **Proposed:** existing workspaces are grouped into agencies by shared people, and
   everyone existing becomes an Admin who can approve, so nobody loses anything on the
   day of the migration.
4. **Proposed:** the routes that change people are built here, with their rules and
   tests, and the screens and invites use them in the next row.
5. **Decided (Dmytro, 2026-11-23):** an agency made by the migration is named from the
   email domain of its oldest member, the rule that names a first workspace and a new
   sign-up's agency. An Admin can rename it.
6. **Decided (Dmytro, 2026-11-23):** only Admins create workspaces, on the web and
   through an assistant. A Member is refused with a message that names the Admins.
7. **Decided (Dmytro, 2026-11-23):** "can approve" is stored and returned here and
   enforced in "Invites and Members screen", the first moment a person without it can
   exist, together with the list of actions that count as critical.

## Done when

- Route tests through the API on the local database:
  - sign-up by each of the three ways makes an agency, an Admin and a first workspace;
  - a person with "all workspaces" reaches a workspace created after they joined; a
    person with chosen workspaces reaches only those, on the web and through MCP with a
    personal access token;
  - a Member is refused when changing people, renaming the agency or creating a
    workspace, on the web and through `create_workspace`; an Admin succeeds;
  - the last Admin cannot be removed or made a Member; with two Admins one can be;
  - a removed person's session and personal access token stop reaching the agency's
    workspaces at once, and keep reaching another agency's;
  - a person in two agencies sees both in `list_workspaces`, each workspace with its
    agency, role and `can_approve`;
  - a workspace of one agency is never reachable through membership of another.
- The migration: built from a database with several shapes (one person with several
  workspaces, two people sharing one, two unrelated people) and checked for the agencies,
  roles and access it produces; `test_models_match_migrated_schema` passes.
- MCP server tests, including the contract entries and input descriptions.
- `make check` passes.

## Out of scope

- Invites, the Members screen, the profile menu with several agencies and Settings ›
  Team (row "Invites and Members screen").
- Billing, balance and usage per agency (Orders 102.4 to 102.55).
- A view across all workspaces; client logins; custom roles; seats.
- Moving a workspace from one agency to another, and deleting an agency or a
  workspace's data (row "Delete workspace data").
- Enforcing "can approve" (decision 7).
- Assistant tools to manage people. They come with the next row, where the screens and
  invites are.

## Risks

- **Access is the one thing this must not get wrong.** Every route trusts one module.
  A reviewer should read `app/crud/workspace.py` and the test "a workspace of one
  agency is never reachable through membership of another" first.
- **The migration decides who can see which client's calls.** It is tested on several
  shapes, and production's shape is the simplest one (one person). The downgrade
  restores `workspace_member` rows for people with "all workspaces".
- **Routes with no screen yet.** The agency routes are reachable by API before their
  screens exist. They are permission-checked and tested here for that reason.

## Outcome

### Deviations from the plan

- **Access is still read from `workspace_member`; the plan said the rule would become
  "in the agency and all workspaces or chosen".** What a person reaches is the same,
  but it is kept as rows: a person with "all workspaces" has a row for every workspace
  of the agency, added again when a workspace is created. Reason: two other places ask
  the opposite question ("who reaches this workspace", for the assistants shown as
  connected), and every existing access query keeps working unchanged. The price is
  that two tables must agree; one module writes both, and a test checks that nobody
  reaches a workspace outside an agency they are in. `app/crud/workspace.py` is
  therefore changed in one way only (see Code review), and the module to read first
  is `app/crud/agency.py`.
- **A person with no workspace left:** sign-in with a password answers 403 with a plain
  sentence, and Google sign-in returns to the sign-in page. The web sign-in form still
  shows its one generic line for any refusal; a proper message there is a screen
  change and belongs with the remove dialog in "Invites and Members screen".
- **`workspace` answers on the web gained `agency_id` and `agency_name`,** for the next
  row's profile menu. No screen reads them yet.
- **Sign-up by the three ways:** the web route and Google account creation are tested;
  the account form on the assistant-connection page calls the same function as the web
  route and has no test of its own here.
- **A person added to an existing workspace by a script** (`create_user` with a
  workspace) joins its agency as a Member with that one workspace.
- **One existing test changed, not weakened:** `test_list_workspaces_returns_the_persons_workspace`
  compared the assistant's whole workspace answer; it now also expects the agency, the
  role and `can_approve`.
- **Deleted:** `crud.add_member` and `crud.create_workspace`, replaced by
  `crud.add_workspace`; nothing else called them.
- **The migration's downgrade** has nothing to restore, because `workspace_member` is
  never changed by the upgrade.

### Check results

Route tests through the API on the local database (`TestClient`; no separate
play-through server, the tests send the same requests, as a web session and as an
assistant with a personal access token):

| What | Result |
|---|---|
| `test_agencies.py` (15 tests): sign-up makes an agency, an Admin and a workspace; "all workspaces" includes a later workspace and "chosen" does not, on the web and for an assistant; one agency never gives access to another, including choosing another agency's workspace (422); a person in two agencies sees each workspace with its agency, role and `can_approve`; a Member reads and changes nothing (403); only an Admin creates a workspace, on the web and through `create_workspace`, and the refusal names the Admins; an Admin of two agencies must say which (422, then 200); rename and change a person; the last Admin cannot be removed or demoted (409); a removed person's session (401) and assistant lose the agency at once and keep their own; no workspace left answers 403 at sign-in; the migration's grouping on five shapes; nobody reaches a workspace outside their agencies | passed |
| Schema drift with migration `0048`, workspaces, multi-tenancy and sign-in tests | passed |
| Whole backend suite | passed (1,092 tests) |
| MCP server tests, with the agency fields and the `agency_id` input | passed (61) |
| Backend `ruff` and `pyright`; frontend types and lint; generated client regenerated | passed |
| Full `make check` (plan, backend lint, types, tests and coverage, MCP server tests, frontend lint and types, generated client) | all passed |

Hosted database, read-only, counts only (2026-11-23): 2 workspaces, 1 person, 2
memberships, no workspace without a member. The migration makes one agency with one
Admin who reaches all workspaces.

### Code review

Run before the pull request. Two bugs found and fixed, each with a test:

- **Chosen workspaces were ignored** for a person who had "all workspaces" unless
  `all_workspaces: false` was sent too: the route answered 200 and the person still
  reached everything. Naming workspaces now means "only these".
- **Access was not tied to the agency where access is decided.** A workspace row for a
  person outside the workspace's agency would have given access, and made the
  assistant's `list_workspaces` fail. The three access queries now also require the
  person to be in the workspace's agency
  (`test_a_workspace_row_alone_gives_no_access`).

Left as they are:

- `DELETE /api/v1/users/me` lets an agency's only Admin delete their own account,
  leaving an agency with no Admin. The route is older than this change and belongs to
  the row that designs deleting an account.
- A password reset and the assistant-connection sign-in still give a session to a
  person with no workspace left; every request is then refused.

### Not done

- "Can approve" is not enforced (decision 7).
- Nothing was tried against production; the migration runs there on deploy.
- The migration was run forward on the local test database only; its downgrade was not
  run.
