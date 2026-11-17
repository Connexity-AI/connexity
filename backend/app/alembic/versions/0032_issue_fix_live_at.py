"""issue fix live at: when the version carrying an issue's fix went live

Revision ID: 0032_issue_fix_live_at
Revises: 0031_run_version_fingerprint
Create Date: 2026-11-17 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0032_issue_fix_live_at'
down_revision = '0031_run_version_fingerprint'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'issue', sa.Column('fix_live_at', sa.DateTime(timezone=True), nullable=True)
    )
    # A fix marked before this counted from the moment it was marked; keep that.
    op.execute(
        "UPDATE issue SET fix_live_at = resolved_at "
        "WHERE resolved_version IS NOT NULL AND resolved_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column('issue', 'fix_live_at')
