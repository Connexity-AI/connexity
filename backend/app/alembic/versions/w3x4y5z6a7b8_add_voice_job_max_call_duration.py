"""add voice job max call duration

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-05-21

"""

import sqlalchemy as sa

from alembic import op

revision = "w3x4y5z6a7b8"
down_revision = "v2w3x4y5z6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_simulation_job",
        sa.Column(
            "max_call_duration_seconds",
            sa.Integer(),
            nullable=False,
            server_default="300",
        ),
    )
    op.alter_column(
        "voice_simulation_job",
        "max_call_duration_seconds",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("voice_simulation_job", "max_call_duration_seconds")
