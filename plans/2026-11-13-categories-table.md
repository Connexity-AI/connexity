# Categories table: one fixed set, in the database

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Categories table" (Stage Check).
- **Design:** No UI change. The categories and their order come from
  `designs/06-categories-everywhere.md`; screens that show them come later.
- **MCP:** adds `list_categories(workspace_id)`.

## Goal

Every issue (and, once the spec exists, every spec rule) belongs to one of a fixed set of
categories, the same for every workspace. The set lives in a database table, so the
Connexity team can rename or reorder a category without a code change. The assistant can
read the list.

"Categories live in a database table so they can be adjusted without code ... One
Connexity-wide set, edited by the Connexity team, the same for every workspace (Decided).
MCP: the assistant can read the list." (roadmap entry, 2026-11-12)

## What exists today

- **No categories anywhere.** An issue is identified by its agent, its check's type and a
  key. Nothing groups issues.
- **One check is registered,** `tool_call_failed`; production has no issues yet.
- **The spec does not exist yet,** so there are no spec rules to point at a category.
- **Every MCP route is scoped to a workspace** in its path, and a test enforces it.

## Changes

### The table (backend)

- **`category`**, not owned by any workspace (no `company_id`; the same for everyone):
  - `key`: a stable identifier such as `booking` or `tools_and_integrations`, which code
    refers to. It never changes once seeded.
  - `name`: what people read, such as "Tools and integrations". It can be edited.
  - `position`: the fixed order, 1 to 14.
  - `kind`: `behaviour` or `technical`.
- **Seeded by the migration** with the 14 categories of design prompt 06, in its order:
  - **Behaviour (1–10):** Greeting and identification, Information collection, Booking,
    Rescheduling and cancelling, Pricing and quotes, Objection handling, Transfers and
    escalation, Compliance and privacy, Conversation flow quality, Ending the call.
  - **Technical (11–13):** Responsiveness, Tools and integrations, Speech recognition.
  - **Other (14):** `behaviour`, since it can hold spec rules too.
- **Editing is done by the Connexity team in the database** (Supabase), with no screen
  or API to edit it. Renaming and reordering are safe. A category that issues point at
  cannot be deleted; the database refuses.

### Issues point at it

- **Each check declares its category by key.** `tool_call_failed` declares
  `tools_and_integrations`. A check whose key is not in the table fails the check
  registry's tests, so a typo cannot ship.
- **`issue.category_id`** is set when the issue is created, from its check's category.
  It is not null, and it uses a foreign key that refuses deletes. The migration fills
  existing issues from their check type; unknown types get Other. Production has none
  today.
- **`IssuePublic`** (web API) gains `category`: key, name and position. That's for the
  Issues page later; nothing on screen changes now.
- **Spec rules point at it when the spec is built.** That feature adds the column.

### MCP

- **`list_categories(workspace_id)`** answers the 14 categories in order, each with its
  key, name and kind, in the standard answer.
  - **Rules:** the set is the same for every workspace; group issues and spec rules
    under these names, in this order; a category with nothing in it is hidden on
    screens.
  - **Next steps:** none needed. The guide is a new short section in the readiness
    guide, or a `categories` guide.
- **It takes `workspace_id`** although the list is the same everywhere. That keeps every
  MCP route scoped to a workspace, as the rule and its test require, and leaves room for
  counts per category (issues in this workspace) later without a new tool.

## Decisions

Decided by Dmytro (roadmap entry, 2026-11-12):

- One Connexity-wide set in a database table, edited by the Connexity team, the same for
  every workspace.
- Name, order, behaviour or technical. Seeded with the 14 categories, with spec rules and
  issues pointing at it.
- The assistant can read the list through MCP.

Proposed by Claude:

- A stable `key` beside the editable `name`, so code never depends on a name.
- "Other" is a behaviour category.
- Each check declares its category; an issue takes its check's category.
- No edit screen or API: the team edits in the database.
- `list_categories` is scoped to a workspace, like every MCP tool.

## Answered questions

Dmytro accepted the recommendation ("Accept, build", 2026-11-13):

1. An issue keeps its check's category; moving one to another category waits for the
   Issues page.

## Done when

- `make check` passes. Backend tests cover:
  - the 14 categories seeded in order, with their kinds;
  - every registered check naming a category that exists;
  - a new issue taking its check's category;
  - deleting a category in use refused by the database;
  - `IssuePublic` carrying the category;
  - `list_categories`: order, fields, an unreachable workspace, and a renamed category
    showing its new name.
- The migration applies, reverses and re-applies locally, with no drift.
- Played through on a running backend through MCP: `list_categories` answers the 14 in
  order; renaming one in the database shows in the next answer.

## Out of scope

- Screens: the Issues page groups, Spec groups and roadmap labels come with their own
  features.
- Spec rules (the spec feature adds their category).
- Moving an issue between categories (question 1).
- An edit screen or API for categories.

## Risks

- **A renamed category changes every workspace at once.** That is intended: one set, one
  name.
- **The key is a promise.** Changing a seeded key breaks the checks that name it. Only a
  migration should ever change one.

## Outcome

### Deviations from the plan

- **`position` is not unique,** so the team can swap two categories in one edit; ties
  fall back to the key.
- **The tests re-seed the categories** at the start of a run. The suite's end-of-run
  `TRUNCATE` removes the migration's seed, as it already does for the predefined metrics.
- **Test checks gained the now-required `category`** (`category="other"` in the two test
  helpers that build a check). Nothing they assert changed.
- **`docs-internal/checks-and-incidents.md`** notes an issue's category.

### Check results

`make check` on the final tree: see the table below.

| Step | Result |
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

New tests:

- `test_categories.py`:
  - the 14 seeded in design order, with positions 1–14 and their kinds;
  - every registered check naming a category that exists;
  - a category in use refused on delete;
  - `list_categories`: the set in order, its fields, guide and rules, a renamed category
    showing its new name, and another workspace not found.
- `test_issues.py`: a new issue carries its check's category (Tools and integrations).
- MCP server: `list_categories` is listed as read-only, and reads the route with the
  user's token.

Migration `0017_categories` applies, reverses and re-applies on the local database, with
no drift. It filled the 2 local issues with Tools and integrations.

**Played through on a running backend** (port 8023, local database), with an MCP token:

| # | Step | Came back |
|---|---|---|
| 1 | `list_categories` | The 14 in design order, kinds right, guide `connexity://guides/categories`, 4 rules |
| 2 | Rename "Other" to "Everything else" in the database, list again | Position 14 reads "Everything else" (then renamed back) |
| 3 | Delete a category the local issues use, in a transaction rolled back | Refused by `issue_category_id_fkey` |
| 4 | Another workspace | 404 |

The backend log had no errors.

`/code-review` (high) raised three findings, all left as they are:

- **`list_categories` is not paginated,** although rule 10 asks for paginated tools. It
  answers 14 fixed rows.
- **The seed exists twice,** in the migration and in `app/models/category.py`. The
  migration must not change with the code, and a test checks the rows against the
  design list.
- **Edits in the database leave no record** of who renamed or reordered a category.
  That is acceptable while only the Connexity team edits it.

**For Dmytro, on app.connexity.ai after merge:** ask the assistant to list the
categories. It answers the 14 in order.

### Not done

- **Spec rules' categories** come with the spec feature.
- **Moving an issue to another category** waits for the Issues page (answered).
- **Screens** that group by category come with their features.
- **Throwaway data in the local dev database:** one play-through user.
