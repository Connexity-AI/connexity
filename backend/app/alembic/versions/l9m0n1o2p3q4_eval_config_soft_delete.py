"""eval config soft delete: deleted_at

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2026-05-05 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "l9m0n1o2p3q4"
down_revision = "k8l9m0n1o2p3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("eval_config", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index(
        op.f("ix_eval_config_deleted_at"),
        "eval_config",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_eval_config_deleted_at"), table_name="eval_config")
    op.drop_column("eval_config", "deleted_at")
