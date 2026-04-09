"""add agent_temperature to agent and agent_version

Revision ID: f2a3b4c5d6e7
Revises: e5f6a7b8c9d0
Create Date: 2026-04-09 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "f2a3b4c5d6e7"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent",
        sa.Column("agent_temperature", sa.Float(), nullable=True),
    )
    op.add_column(
        "agent_version",
        sa.Column("agent_temperature", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_version", "agent_temperature")
    op.drop_column("agent", "agent_temperature")
