"""custom_metric: add deleted_at and switch to global name uniqueness

Revision ID: i6j7k8l9m0n1
Revises: h5i6j7k8l9m0
Create Date: 2026-05-01 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "i6j7k8l9m0n1"
down_revision = "h5i6j7k8l9m0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "custom_metric",
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_custom_metric_deleted_at"),
        "custom_metric",
        ["deleted_at"],
        unique=False,
    )

    # Drop the old per-owner unique constraint and replace with a global
    # partial unique index on name, scoped to live (non-deleted) rows.
    op.drop_constraint(
        "uq_custom_metric_owner_name", "custom_metric", type_="unique"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_custom_metric_name_active "
        "ON custom_metric (name) WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_custom_metric_name_active")
    op.create_unique_constraint(
        "uq_custom_metric_owner_name",
        "custom_metric",
        ["created_by", "name"],
    )
    op.drop_index(op.f("ix_custom_metric_deleted_at"), table_name="custom_metric")
    op.drop_column("custom_metric", "deleted_at")
