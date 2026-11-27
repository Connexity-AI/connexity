"""An issue's subject: the spec rule a "Spec rule broken" issue is named after

Revision ID: 0058_issue_subject
Revises: 0057_rule_check_and_inputs
Create Date: 2026-11-27 00:00:00.000000

Plan: plans/2026-11-26-spec-check.md.
"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '0058_issue_subject'
down_revision = '0057_rule_check_and_inputs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('issue', sa.Column('subject', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('issue', 'subject')
