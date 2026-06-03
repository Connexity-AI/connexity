"""add label to call

Revision ID: x3y4z5a6b7c8
Revises: w2x3y4z5a6b7
Create Date: 2026-06-03

"""

from alembic import op
import sqlalchemy as sa

revision = "x3y4z5a6b7c8"
down_revision = "w2x3y4z5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "call",
        sa.Column("label", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("call", "label")
