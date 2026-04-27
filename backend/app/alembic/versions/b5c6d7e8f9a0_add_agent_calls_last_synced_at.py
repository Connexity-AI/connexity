"""add agent.calls_last_synced_at

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-04-27 00:30:00.000000

Stale-while-revalidate marker for the Observer call list endpoint. Updated
each time GET /agents/{id}/calls schedules a background Retell sync; the TTL
gate uses it to dedup concurrent requests and back off after failures.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5c6d7e8f9a0'
down_revision = 'a4b5c6d7e8f9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'agent',
        sa.Column('calls_last_synced_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('agent', 'calls_last_synced_at')
