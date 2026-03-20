# Database Migration Workflow

Alembic manages PostgreSQL schema migrations. Migration files live in `backend/app/alembic/versions/`.

## Creating a Migration

After modifying SQLModel models in `backend/app/models/`:

```bash
make db-migrate MSG="add workspace table"
# or: cd backend && alembic revision --autogenerate -m "add workspace table"
```

**Always review the generated file** before committing. Autogenerate does not handle every case — check for:

- Correct table/column creation and deletion
- ENUM type drops in `downgrade()` (see below)
- Index creation (GIN indexes from `__table_args__` may need manual addition)
- Correct foreign key constraint ordering in downgrade (children before parents)

## Applying Migrations

```bash
make db-upgrade          # run alembic upgrade head
make db-seed             # run migrations + seed data (prestart.sh)
```

## Downgrading

```bash
cd backend
alembic downgrade -1     # roll back one revision
alembic downgrade base   # roll back all revisions
```

## Verifying No Drift

After applying migrations, check that models and DB schema are in sync:

```bash
cd backend && alembic revision --autogenerate -m "drift check"
```

If the generated migration contains only `pass` in both `upgrade()` and `downgrade()`, there is no drift. Delete the empty file.

## Handling ENUM Types

Alembic autogenerate **does not** emit `DROP TYPE` statements in `downgrade()` for PostgreSQL ENUM types. After generating a migration that creates enums, manually add drops at the end of `downgrade()`:

```python
sa.Enum(name='myenum').drop(op.get_bind(), checkfirst=True)
```

Without this, `alembic downgrade base` leaves orphan enum types in the database.

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
