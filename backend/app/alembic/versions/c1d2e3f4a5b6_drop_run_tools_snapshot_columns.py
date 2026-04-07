"""drop run.tools_snapshot and run.tools_snapshot_hash

Revision ID: c1d2e3f4a5b6
Revises: b7c8d9e0f1a2
Create Date: 2026-04-07 14:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("run", "tools_snapshot_hash")
    op.drop_column("run", "tools_snapshot")


def downgrade() -> None:
    op.add_column(
        "run",
        sa.Column(
            "tools_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "run",
        sa.Column("tools_snapshot_hash", sa.String(length=64), nullable=True),
    )
