"""call soft delete: nullable integration_id + deleted_at

Revision ID: a7b8c9d0e1f2
Revises: b5c6d7e8f9a0
Create Date: 2026-04-27 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("call", "integration_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("call", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_call_deleted_at"), "call", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_call_deleted_at"), table_name="call")
    op.drop_column("call", "deleted_at")
    op.alter_column("call", "integration_id", existing_type=sa.Uuid(), nullable=False)
