"""add requirements_status to agent_version

Revision ID: req_status_001
Revises: 8a58cbd53c5e
Create Date: 2026-06-16

Tracks the lifecycle of a version's extracted requirement snapshot
(pending/extracting/ready/empty/failed) so the UI can distinguish a failed
extraction from one that genuinely produced nothing, and offer a retry.
"""

import sqlalchemy as sa
from alembic import op

revision = "req_status_001"
down_revision = "8a58cbd53c5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_version",
        sa.Column(
            "requirements_status",
            sa.Text(),
            nullable=False,
            server_default="pending",
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_version", "requirements_status")
