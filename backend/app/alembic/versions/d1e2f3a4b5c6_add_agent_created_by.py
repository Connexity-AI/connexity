"""add agent.created_by for ownership tracking

Revision ID: d1e2f3a4b5c6
Revises: 0b1519d085ff
Create Date: 2026-04-23 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "d1e2f3a4b5c6"
down_revision = "0b1519d085ff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent", sa.Column("created_by", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_agent_created_by"), "agent", ["created_by"], unique=False)
    op.create_foreign_key(
        "fk_agent_created_by_user_id",
        "agent",
        "user",
        ["created_by"],
        ["id"],
    )

    # Backfill created_by from the earliest AgentVersion.created_by for each agent
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE agent a
            SET created_by = (
                SELECT av.created_by
                FROM agent_version av
                WHERE av.agent_id = a.id
                  AND av.created_by IS NOT NULL
                ORDER BY av.created_at ASC
                LIMIT 1
            )
            WHERE a.created_by IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_agent_created_by_user_id", "agent", type_="foreignkey")
    op.drop_index(op.f("ix_agent_created_by"), table_name="agent")
    op.drop_column("agent", "created_by")
