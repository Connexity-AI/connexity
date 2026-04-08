"""agent draft/publish lifecycle: status, has_draft, nullable version (CS-80)

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-04-07 14:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add status column to agent_version (default 'published' for existing rows)
    op.add_column(
        "agent_version",
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="published",
            nullable=False,
        ),
    )

    # 2. Make version column nullable (drafts have NULL version)
    op.alter_column(
        "agent_version",
        "version",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # 3. Drop the existing unique constraint on (agent_id, version) and recreate
    #    as a partial unique index that only applies to non-NULL versions
    op.drop_constraint(
        "uq_agent_version_agent_version", "agent_version", type_="unique"
    )
    op.create_index(
        "uq_agent_version_agent_version",
        "agent_version",
        ["agent_id", "version"],
        unique=True,
        postgresql_where=sa.text("version IS NOT NULL"),
    )

    # 4. Partial unique index: at most one draft per agent
    op.create_index(
        "ix_agent_version_one_draft_per_agent",
        "agent_version",
        ["agent_id"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )

    # 5. Add has_draft column to agent table
    op.add_column(
        "agent",
        sa.Column(
            "has_draft",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("agent", "has_draft")
    op.drop_index(
        "ix_agent_version_one_draft_per_agent", table_name="agent_version"
    )
    op.drop_index(
        "uq_agent_version_agent_version", table_name="agent_version"
    )

    # Delete any draft rows before restoring NOT NULL + unique constraint
    op.execute(
        sa.text("DELETE FROM agent_version WHERE status = 'draft'")
    )

    op.create_unique_constraint(
        "uq_agent_version_agent_version",
        "agent_version",
        ["agent_id", "version"],
    )
    op.alter_column(
        "agent_version",
        "version",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_column("agent_version", "status")
