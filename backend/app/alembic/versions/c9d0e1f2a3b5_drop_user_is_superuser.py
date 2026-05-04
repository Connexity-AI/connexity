"""drop user.is_superuser

Revision ID: c9d0e1f2a3b5
Revises: b8c9d0e1f2a3
Create Date: 2026-04-28 00:00:01.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "c9d0e1f2a3b5"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: some dev DBs were already manually altered to drop this
    # column before the migration was authored; ``IF EXISTS`` lets the chain
    # advance regardless of starting state.
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS is_superuser')


def downgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
