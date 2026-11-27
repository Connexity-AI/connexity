"""A finding's false-positive mark: who, when, why, the clarification and the approver

Revision ID: 0059_finding_false_positive
Revises: 0058_issue_subject
Create Date: 2026-11-27 00:00:00.000000

Plan: plans/2026-11-27-false-positives.md.
"""
import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision = '0059_finding_false_positive'
down_revision = '0058_issue_subject'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'finding', sa.Column('false_positive_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('finding', sa.Column('false_positive_by', sa.Uuid(), nullable=True))
    op.add_column(
        'finding', sa.Column('false_positive_by_email', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True)
    )
    op.add_column(
        'finding', sa.Column('false_positive_assistant', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True)
    )
    op.add_column('finding', sa.Column('false_positive_reason', sa.Text(), nullable=True))
    op.add_column(
        'finding', sa.Column('false_positive_clarification_id', sa.Uuid(), nullable=True)
    )
    op.add_column(
        'finding',
        sa.Column('false_positive_approved_by', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    )
    op.create_foreign_key(
        'finding_false_positive_by_fkey', 'finding', 'user', ['false_positive_by'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'finding_false_positive_clarification_id_fkey', 'finding', 'clarification',
        ['false_positive_clarification_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('finding_false_positive_clarification_id_fkey', 'finding', type_='foreignkey')
    op.drop_constraint('finding_false_positive_by_fkey', 'finding', type_='foreignkey')
    for column in (
        'false_positive_approved_by', 'false_positive_clarification_id',
        'false_positive_reason', 'false_positive_assistant', 'false_positive_by_email',
        'false_positive_by', 'false_positive_at',
    ):
        op.drop_column('finding', column)
