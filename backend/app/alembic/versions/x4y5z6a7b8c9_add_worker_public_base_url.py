"""add worker_public_base_url to voice_simulation_job

Revision ID: x4y5z6a7b8c9
Revises: w3x4y5z6a7b8
Create Date: 2026-05-26

"""

import sqlalchemy as sa

from alembic import op

revision = "x4y5z6a7b8c9"
down_revision = "w3x4y5z6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_simulation_job",
        sa.Column("worker_public_base_url", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("voice_simulation_job", "worker_public_base_url")
