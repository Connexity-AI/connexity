"""Who ran a run of scenarios: the assistant and its session, beside the person

Revision ID: 0037_run_who
Revises: 0036_work_task_states
Create Date: 2026-11-19 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0037_run_who'
down_revision = '0036_work_task_states'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'run',
        sa.Column(
            'assistant_name', sa.String(length=255), nullable=True
        ),
    )
    op.add_column(
        'run',
        sa.Column(
            'session_name', sa.String(length=40), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column('run', 'session_name')
    op.drop_column('run', 'assistant_name')
