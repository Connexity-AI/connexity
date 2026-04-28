"""drop integration.user_id (platform-scoped integrations)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-28 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM integration")
    op.drop_index(op.f("ix_integration_user_id"), table_name="integration")
    op.drop_column("integration", "user_id")


def downgrade() -> None:
    op.add_column(
        "integration",
        sa.Column("user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_integration_user_id",
        "integration",
        "user",
        ["user_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_integration_user_id"),
        "integration",
        ["user_id"],
        unique=False,
    )
