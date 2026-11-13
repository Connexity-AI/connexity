"""an agent keeps the state of its first scan; a workspace, when it first finished

Revision ID: 0014_agent_first_scan
Revises: 0013_agent_last_webhook_call
Create Date: 2026-11-13 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0014_agent_first_scan'
down_revision = '0013_agent_last_webhook_call'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('agent', sa.Column('scan_from', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agent', sa.Column('scan_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agent', sa.Column('scan_total', sa.Integer(), nullable=True))
    op.add_column('agent', sa.Column('scan_cursor', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agent', sa.Column('scan_done_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('company', sa.Column('first_scan_done_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('company', 'first_scan_done_at')
    op.drop_column('agent', 'scan_done_at')
    op.drop_column('agent', 'scan_cursor')
    op.drop_column('agent', 'scan_total')
    op.drop_column('agent', 'scan_until')
    op.drop_column('agent', 'scan_from')
