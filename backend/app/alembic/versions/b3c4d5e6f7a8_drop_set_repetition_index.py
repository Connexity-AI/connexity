"""Drop set_repetition_index from test_case_result (now always 0)

Revision ID: b3c4d5e6f7a8
Revises: a6b7c8d9e0f1
Create Date: 2026-04-16 10:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "b3c4d5e6f7a8"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("test_case_result", "set_repetition_index")


def downgrade() -> None:
    op.add_column(
        "test_case_result",
        sa.Column(
            "set_repetition_index",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
