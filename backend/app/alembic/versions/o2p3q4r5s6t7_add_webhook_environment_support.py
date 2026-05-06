"""add webhook environment support

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-05-06 17:05:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "o2p3q4r5s6t7"
down_revision = "n1o2p3q4r5s6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE platform ADD VALUE IF NOT EXISTS 'webhook'")
    op.add_column("environment", sa.Column("endpoint_url", sa.String(length=2048), nullable=True))
    op.alter_column("environment", "integration_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column(
        "environment",
        "platform_agent_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.alter_column(
        "environment",
        "platform_agent_name",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "environment",
        "platform_agent_name",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "environment",
        "platform_agent_id",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column("environment", "integration_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_column("environment", "endpoint_url")
    # note: enum values cannot be removed safely from PostgreSQL in downgrade.
