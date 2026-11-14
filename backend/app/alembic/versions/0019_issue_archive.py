"""issue archive: duration and spike baseline; decision records name the assistant

Revision ID: 0019_issue_archive
Revises: 0018_issue_state_names
Create Date: 2026-11-14 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0019_issue_archive'
down_revision = '0018_issue_state_names'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('issue', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('issue', sa.Column('archive_until_spike', sa.Boolean(), nullable=True))
    op.add_column('issue', sa.Column('archive_baseline_share', sa.Float(), nullable=True))
    op.add_column('decision_record', sa.Column('assistant_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
    op.add_column('decision_record', sa.Column('detail', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True))
    # Archived before durations existed: they stay archived until someone unarchives them.
    op.execute("UPDATE issue SET archive_until_spike = false WHERE state = 'archived'")


def downgrade():
    op.drop_column('decision_record', 'detail')
    op.drop_column('decision_record', 'assistant_name')
    op.drop_column('issue', 'archive_baseline_share')
    op.drop_column('issue', 'archive_until_spike')
    op.drop_column('issue', 'archived_at')
