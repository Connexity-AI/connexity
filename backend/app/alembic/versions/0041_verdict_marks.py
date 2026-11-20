"""A rule verdict can be marked as not evidence (it rests on a default fake), with the
tools that answered with it

Revision ID: 0041_verdict_marks
Revises: 0040_remove_old_eval_stack
Create Date: 2026-11-20 21:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0041_verdict_marks'
down_revision = '0040_remove_old_eval_stack'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('rule_verdict', sa.Column('mark', sa.String(length=32), nullable=True))
    op.add_column(
        'rule_verdict',
        sa.Column('mark_detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('rule_verdict', 'mark_detail')
    op.drop_column('rule_verdict', 'mark')
