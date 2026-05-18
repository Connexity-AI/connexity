"""remove duplicated environment provider target fields

Revision ID: s8t9u0v1w2x3
Revises: r1s2t3u4v5w6
Create Date: 2026-05-12

"""

import sqlalchemy as sa
from alembic import op

revision = "s8t9u0v1w2x3"
down_revision = "r1s2t3u4v5w6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f("ix_environment_platform_agent_id"), table_name="environment")
    op.drop_index(op.f("ix_environment_integration_id"), table_name="environment")
    op.drop_column("environment", "platform_agent_name")
    op.drop_column("environment", "platform_agent_id")
    op.drop_column("environment", "integration_id")


def downgrade() -> None:
    op.add_column(
        "environment",
        sa.Column("integration_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "environment",
        sa.Column("platform_agent_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "environment",
        sa.Column("platform_agent_name", sa.String(length=255), nullable=True),
    )
    op.create_foreign_key(
        "fk_environment_integration_id_integration",
        "environment",
        "integration",
        ["integration_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_environment_integration_id"),
        "environment",
        ["integration_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_environment_platform_agent_id"),
        "environment",
        ["platform_agent_id"],
        unique=False,
    )
