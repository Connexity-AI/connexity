"""agent prompt type and canonical provider target fields

Revision ID: r1s2t3u4v5w6
Revises: q5r6s7t8u9v0
Create Date: 2026-05-12

"""

import sqlalchemy as sa
from alembic import op

revision = "r1s2t3u4v5w6"
down_revision = "q5r6s7t8u9v0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent",
        sa.Column(
            "prompt_type",
            sa.String(length=64),
            nullable=False,
            server_default="single_prompt",
        ),
    )
    op.add_column(
        "agent",
        sa.Column("integration_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "agent",
        sa.Column("platform_agent_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "agent",
        sa.Column("platform_agent_name", sa.String(length=255), nullable=True),
    )
    op.create_foreign_key(
        "fk_agent_integration_id_integration",
        "agent",
        "integration",
        ["integration_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_agent_integration_id"), "agent", ["integration_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_integration_id"), table_name="agent")
    op.drop_constraint("fk_agent_integration_id_integration", "agent", type_="foreignkey")
    op.drop_column("agent", "platform_agent_name")
    op.drop_column("agent", "platform_agent_id")
    op.drop_column("agent", "integration_id")
    op.drop_column("agent", "prompt_type")
