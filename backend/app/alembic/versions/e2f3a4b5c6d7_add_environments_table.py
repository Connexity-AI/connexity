"""add environments table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-04-23 00:01:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "environment",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("integration_id", sa.Uuid(), nullable=False),
        sa.Column("platform_agent_id", sa.String(length=255), nullable=False),
        sa.Column("platform_agent_name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agent.id"]),
        sa.ForeignKeyConstraint(["integration_id"], ["integration.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_environment_agent_id"), "environment", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_environment_integration_id"), "environment", ["integration_id"], unique=False
    )
    op.create_index(
        op.f("ix_environment_platform_agent_id"),
        "environment",
        ["platform_agent_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_environment_platform_agent_id"), table_name="environment")
    op.drop_index(op.f("ix_environment_integration_id"), table_name="environment")
    op.drop_index(op.f("ix_environment_agent_id"), table_name="environment")
    op.drop_table("environment")
