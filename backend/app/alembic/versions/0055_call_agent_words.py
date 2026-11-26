"""The agent's word count on each call, so short calls are not graded

Revision ID: 0055_call_agent_words
Revises: 0054_top_ups
Create Date: 2026-11-26 18:00:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '0055_call_agent_words'
down_revision = '0054_top_ups'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('call', sa.Column('agent_words', sa.Integer(), nullable=True))
    # Counted as `app/services/grading.py` counts: words of the agent's turns, split on
    # whitespace. Only calls with a stored trace get a count.
    op.execute(
        """
        UPDATE call SET agent_words = coalesce((
            SELECT count(*)
            FROM call_event e,
                 regexp_split_to_table(e.text, '\\s+') AS word
            WHERE e.call_id = call.id
              AND e.speaker = 'agent'
              AND e.text IS NOT NULL
              AND word <> ''
        ), 0)
        WHERE schema_version IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column('call', 'agent_words')
