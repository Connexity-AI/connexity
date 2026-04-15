"""add editor_guidelines to agent

Revision ID: a1b2c3d4e5f7
Revises: 93a62d06596f
Create Date: 2026-04-15 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f7"
down_revision = "93a62d06596f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent",
        sa.Column("editor_guidelines", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent", "editor_guidelines")
