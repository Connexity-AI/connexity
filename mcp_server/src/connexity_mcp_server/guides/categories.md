# Categories

Every issue, and every spec rule once the spec exists, belongs to one of a fixed set of
categories. The set is the same for every workspace and only the Connexity team changes
it, so people learn one set of names and see it everywhere.

Call `list_categories` with a `workspace_id` for the set, in order. Each category has:

- `key`: a stable identifier that never changes;
- `name`: what people read;
- `position`: the fixed order;
- `kind`: `behaviour` (what the agent does, what its spec describes) or `technical`
  (problems any agent can have, whatever its spec says).

## How to use them

- **Group by category, in its order,** whenever you list issues or spec rules for the
  person, and use the category names. Hide a category with nothing in it; never reorder
  the rest.
- **An issue belongs to the category of the check that found it.** For example, a failed
  tool call is under Tools and integrations.
- **When you write spec rules,** put each one under the behaviour category it describes.
  Use Other only when none fits.
