"""rename eval_set → eval_config, add agent_id + config JSONB,
rename firstturn enum value PERSONA → USER

Revision ID: 3fd6a2a5fda5
Revises: 07e97e39ccf5
Create Date: 2026-04-16 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "3fd6a2a5fda5"
down_revision = "07e97e39ccf5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Create eval_config table (agent_id nullable for now) ─────
    op.create_table(
        "eval_config",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),  # nullable during migration
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("config", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["agent_id"], ["agent.id"], name="fk_eval_config_agent_id_agent"
        ),
    )
    op.create_index("ix_eval_config_name", "eval_config", ["name"])
    op.create_index("ix_eval_config_agent_id", "eval_config", ["agent_id"])

    # ── 2. Create eval_config_member table ──────────────────────────
    op.create_table(
        "eval_config_member",
        sa.Column("eval_config_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("eval_config_id", "test_case_id"),
        sa.ForeignKeyConstraint(
            ["eval_config_id"],
            ["eval_config.id"],
            name="fk_eval_config_member_eval_config_id",
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_case.id"],
            name="fk_eval_config_member_test_case_id",
        ),
    )
    op.create_index(
        "ix_eval_config_member_eval_config_id",
        "eval_config_member",
        ["eval_config_id"],
    )
    op.create_check_constraint(
        "ck_eval_config_member_repetitions_ge_1",
        "eval_config_member",
        "repetitions >= 1",
    )

    # ── 3. Migrate data: eval_set → eval_config ────────────────────
    # Copy rows, populating agent_id from the most-recent run referencing
    # each eval_set.  For eval_sets with no runs, fall back to the agent_id
    # of the first test case linked through eval_set_member.
    conn.execute(
        sa.text("""
            INSERT INTO eval_config (id, name, description, version, created_at, updated_at, agent_id)
            SELECT
                es.id,
                es.name,
                es.description,
                es.version,
                es.created_at,
                es.updated_at,
                COALESCE(
                    (SELECT r.agent_id FROM run r
                     WHERE r.eval_set_id = es.id
                     ORDER BY r.created_at DESC LIMIT 1),
                    (SELECT tc.agent_id FROM eval_set_member esm
                     JOIN test_case tc ON tc.id = esm.test_case_id
                     WHERE esm.eval_set_id = es.id AND tc.agent_id IS NOT NULL
                     ORDER BY tc.created_at DESC LIMIT 1)
                )
            FROM eval_set es
        """)
    )

    # ── 4. Migrate data: eval_set_member → eval_config_member ──────
    conn.execute(
        sa.text("""
            INSERT INTO eval_config_member (eval_config_id, test_case_id, position, repetitions)
            SELECT eval_set_id, test_case_id, position, repetitions
            FROM eval_set_member
        """)
    )

    # ── 5. Drop the FK on run.eval_set_id before renaming ──────────
    op.drop_constraint("fk_run_eval_set_id_eval_set", "run", type_="foreignkey")

    # ── 6. Rename run columns ──────────────────────────────────────
    op.alter_column(
        "run",
        "eval_set_id",
        new_column_name="eval_config_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.alter_column(
        "run",
        "eval_set_version",
        new_column_name="eval_config_version",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    # Rename the index
    op.execute(
        sa.text(
            "ALTER INDEX ix_run_eval_set_id RENAME TO ix_run_eval_config_id"
        )
    )

    # Create FK from run → eval_config
    op.create_foreign_key(
        "fk_run_eval_config_id_eval_config",
        "run",
        "eval_config",
        ["eval_config_id"],
        ["id"],
    )

    # ── 7. Drop old tables (member first due to FK) ────────────────
    op.drop_constraint(
        "fk_eval_set_member_eval_set_id_eval_set",
        "eval_set_member",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_eval_set_member_test_case_id_test_case",
        "eval_set_member",
        type_="foreignkey",
    )
    op.drop_table("eval_set_member")
    op.drop_table("eval_set")

    # ── 8. Make eval_config.agent_id NOT NULL ──────────────────────
    # (after migration, all rows should have an agent_id; orphans with
    #  NULL are deleted first to keep the migration safe)
    conn.execute(
        sa.text("DELETE FROM eval_config WHERE agent_id IS NULL")
    )
    op.alter_column(
        "eval_config",
        "agent_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )

    # ── 9. Rename firstturn enum value PERSONA → USER ──────────────
    conn.execute(
        sa.text("ALTER TYPE firstturn RENAME VALUE 'PERSONA' TO 'USER'")
    )


def downgrade() -> None:
    conn = op.get_bind()

    # ── 9. Revert firstturn enum value USER → PERSONA ──────────────
    conn.execute(
        sa.text("ALTER TYPE firstturn RENAME VALUE 'USER' TO 'PERSONA'")
    )

    # ── 8. Make eval_config.agent_id nullable again ────────────────
    op.alter_column(
        "eval_config",
        "agent_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # ── 7. Recreate eval_set + eval_set_member tables ──────────────
    op.create_table(
        "eval_set",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_set_name", "eval_set", ["name"])

    op.create_table(
        "eval_set_member",
        sa.Column("eval_set_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("eval_set_id", "test_case_id"),
        sa.ForeignKeyConstraint(
            ["eval_set_id"],
            ["eval_set.id"],
            name="fk_eval_set_member_eval_set_id_eval_set",
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_case.id"],
            name="fk_eval_set_member_test_case_id_test_case",
        ),
    )
    op.create_index(
        "ix_eval_set_member_eval_set_id", "eval_set_member", ["eval_set_id"]
    )
    op.create_check_constraint(
        "ck_eval_set_member_repetitions_ge_1",
        "eval_set_member",
        "repetitions >= 1",
    )

    # Copy data back
    conn.execute(
        sa.text("""
            INSERT INTO eval_set (id, name, description, version, created_at, updated_at)
            SELECT id, name, description, version, created_at, updated_at
            FROM eval_config
        """)
    )
    conn.execute(
        sa.text("""
            INSERT INTO eval_set_member (eval_set_id, test_case_id, position, repetitions)
            SELECT eval_config_id, test_case_id, position, repetitions
            FROM eval_config_member
        """)
    )

    # ── 6. Revert run column renames ───────────────────────────────
    op.drop_constraint(
        "fk_run_eval_config_id_eval_config", "run", type_="foreignkey"
    )
    op.alter_column(
        "run",
        "eval_config_id",
        new_column_name="eval_set_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.alter_column(
        "run",
        "eval_config_version",
        new_column_name="eval_set_version",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.execute(
        sa.text(
            "ALTER INDEX ix_run_eval_config_id RENAME TO ix_run_eval_set_id"
        )
    )
    op.create_foreign_key(
        "fk_run_eval_set_id_eval_set",
        "run",
        "eval_set",
        ["eval_set_id"],
        ["id"],
    )

    # ── Drop new tables ────────────────────────────────────────────
    op.drop_table("eval_config_member")
    op.drop_table("eval_config")
