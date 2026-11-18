"""Work's task states: "waiting for you" is only for clarifications, so no task an
assistant holds waits; and when its session last asked for its next task

Revision ID: 0036_work_task_states
Revises: 0035_no_workspace_model_keys
Create Date: 2026-11-18 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0036_work_task_states'
down_revision = '0035_no_workspace_model_keys'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'assistant_task',
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    )
    # A held issue fix that waited for the person is in progress with its session
    # again (Dmytro, 2026-11-18: "Waiting for you IS ONLY FOR CLARIFICATIONS").
    op.execute("UPDATE assistant_task SET state = 'in_progress' WHERE state = 'waiting'")
    op.drop_index(
        'ix_assistant_task_one_open',
        table_name='assistant_task',
        postgresql_where=sa.text("state IN ('in_progress', 'waiting')"),
    )
    op.create_index(
        'ix_assistant_task_one_open',
        'assistant_task',
        ['company_id', 'task_key'],
        unique=True,
        postgresql_where=sa.text("state = 'in_progress'"),
    )


def downgrade() -> None:
    op.drop_index(
        'ix_assistant_task_one_open',
        table_name='assistant_task',
        postgresql_where=sa.text("state = 'in_progress'"),
    )
    op.create_index(
        'ix_assistant_task_one_open',
        'assistant_task',
        ['company_id', 'task_key'],
        unique=True,
        postgresql_where=sa.text("state IN ('in_progress', 'waiting')"),
    )
    op.drop_column('assistant_task', 'last_seen_at')
