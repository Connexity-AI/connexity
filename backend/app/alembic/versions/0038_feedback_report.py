"""Assistant feedback: bugs and feature requests assistants report about Connexity

Revision ID: 0038_feedback_report
Revises: 0037_run_who
Create Date: 2026-11-19 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0038_feedback_report'
down_revision = '0037_run_who'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'feedback_report',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('what_happened', sa.Text(), nullable=True),
        sa.Column('wanted', sa.Text(), nullable=True),
        sa.Column('tool', sa.String(length=100), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sent_by', sa.Uuid(), nullable=True),
        sa.Column('assistant_name', sa.String(length=255), nullable=True),
        sa.Column('session_name', sa.String(length=40), nullable=True),
        sa.Column('connexity_version', sa.String(length=100), nullable=False),
        sa.Column(
            'received_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('notion_page_id', sa.String(length=64), nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tries', sa.Integer(), server_default='0', nullable=False),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['company.id']),
        sa.ForeignKeyConstraint(['sent_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_feedback_report_company_id'), 'feedback_report', ['company_id'], unique=False
    )
    op.create_index(
        op.f('ix_feedback_report_sent_by'), 'feedback_report', ['sent_by'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_feedback_report_sent_by'), table_name='feedback_report')
    op.drop_index(op.f('ix_feedback_report_company_id'), table_name='feedback_report')
    op.drop_table('feedback_report')
