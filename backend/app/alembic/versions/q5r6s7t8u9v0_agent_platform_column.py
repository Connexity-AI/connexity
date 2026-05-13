"""add platform column to agent

Revision ID: q5r6s7t8u9v0
Revises: p4q5r6s7t8u9
Create Date: 2026-05-11

"""

import sqlalchemy as sa
from alembic import op

revision = "q5r6s7t8u9v0"
down_revision = "p4q5r6s7t8u9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent",
        sa.Column("platform", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent", "platform")
