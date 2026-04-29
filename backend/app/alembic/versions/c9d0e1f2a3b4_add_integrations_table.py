"""add integrations table

Revision ID: c9d0e1f2a3b4
Revises: 07e97e39ccf5
Create Date: 2026-04-21 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "c9d0e1f2a3b4"
down_revision = "07e97e39ccf5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration",
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("masked_api_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_integration_provider"), "integration", ["provider"], unique=False)
    op.create_index(op.f("ix_integration_user_id"), "integration", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_integration_user_id"), table_name="integration")
    op.drop_index(op.f("ix_integration_provider"), table_name="integration")
    op.drop_table("integration")
