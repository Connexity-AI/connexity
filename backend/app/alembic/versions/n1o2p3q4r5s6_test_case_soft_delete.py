"""test case soft delete: deleted_at

Revision ID: n1o2p3q4r5s6
Revises: m0n1o2p3q4r5
Create Date: 2026-05-05 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "n1o2p3q4r5s6"
down_revision = "m0n1o2p3q4r5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_case", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index(
        op.f("ix_test_case_deleted_at"),
        "test_case",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_test_case_deleted_at"), table_name="test_case")
    op.drop_column("test_case", "deleted_at")
