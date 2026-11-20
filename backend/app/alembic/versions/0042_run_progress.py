"""A run's heartbeat, and each simulated call's judge time and throttle count

Revision ID: 0042_run_progress
Revises: 0041_verdict_marks
Create Date: 2026-11-20 23:00:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '0042_run_progress'
down_revision = '0041_verdict_marks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('run', sa.Column('heartbeat_at', sa.DateTime(), nullable=True))
    op.add_column('test_case_result', sa.Column('judge_ms', sa.Integer(), nullable=True))
    op.add_column('test_case_result', sa.Column('throttled', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('test_case_result', 'throttled')
    op.drop_column('test_case_result', 'judge_ms')
    op.drop_column('run', 'heartbeat_at')
