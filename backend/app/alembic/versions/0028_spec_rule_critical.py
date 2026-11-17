"""spec rule critical: whether a failure of the rule must stop a release

Revision ID: 0028_spec_rule_critical
Revises: 0027_answer_text
Create Date: 2026-11-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0028_spec_rule_critical'
down_revision = '0027_answer_text'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'spec_rule',
        sa.Column('critical', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )


def downgrade() -> None:
    # A "marked" spec version only changed marks. Without the column it is an unchanged
    # copy of the version before it, which is what "adopted" holds.
    op.execute("UPDATE spec SET origin = 'adopted' WHERE origin = 'marked'")
    op.drop_column('spec_rule', 'critical')
