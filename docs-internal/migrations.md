# Database Migration Workflow

Alembic manages PostgreSQL schema migrations. Migration files live in `backend/app/alembic/versions/`.

The history starts at `0001_baseline`, generated from the models during the 2.0 rebuild.
It replaced the 64 revisions of Connexity 1.x. A database created by those old revisions
cannot be upgraded: recreate it.

## Creating a Migration

After modifying SQLModel models in `backend/app/models/`:

```bash
make db-migrate MSG="add workspace table"
# or: cd backend && alembic revision --autogenerate -m "add workspace table"
```

**Always review the generated file** before committing. Autogenerate does not handle every case — check for:

- Correct table/column creation and deletion
- Index creation (GIN indexes from `__table_args__` may need manual addition)
- Correct foreign key constraint ordering in downgrade (children before parents)

## Applying Migrations

```bash
make db-upgrade          # run alembic upgrade head
```

## Downgrading

```bash
cd backend
alembic downgrade -1     # roll back one revision
alembic downgrade base   # roll back all revisions
```

## Verifying No Drift

Models and migrations must always agree. Two things enforce it:

```bash
cd backend && uv run alembic check
```

and the test `test_models_match_migrated_schema` in
`backend/app/tests/crud/test_schema_conventions.py`, which fails the suite when a model
changes without a migration or the reverse.

Anything a migration creates must also be declared on the model (indexes, partial
indexes, `ondelete` rules, constraints). The 1.x history drifted because constraints
were added in migrations only.

## Enum columns

Every enum column uses `enum_type(...)` from `app.models.columns`:

```python
status: RunStatus = Field(default=RunStatus.PENDING, sa_type=enum_type(RunStatus))
```

It is stored as a `VARCHAR(32)` holding the member's value (`"pending"`, not `"PENDING"`).
No PostgreSQL ENUM types are created, so adding a member needs no `ALTER TYPE` migration
and `downgrade()` has no types to drop. A test fails if an enum column is declared any
other way.

## Resolving Migration Conflicts

If two branches both add migrations, the second branch to merge will have a `down_revision` pointing to a revision that is no longer the head.

To resolve:
1. Delete the conflicting migration on your branch
2. Rebase onto the target branch
3. Regenerate the migration: `make db-migrate MSG="your description"`

## Pre-commit Checklist

Before committing a new migration:

- [ ] `alembic upgrade head` succeeds on a clean database
- [ ] `alembic downgrade base` leaves zero tables and enum types
- [ ] `alembic revision --autogenerate` shows no drift (empty migration)
- [ ] Downgrade drops all ENUM types created in upgrade
- [ ] `ruff check .` and `ruff format --check .` pass
