"""run version fingerprint: the content a run of scenarios tested

Revision ID: 0031_run_version_fingerprint
Revises: 0030_text_runner
Create Date: 2026-11-17 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0031_run_version_fingerprint'
down_revision = '0030_text_runner'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'run', sa.Column('version_fingerprint', sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('run', 'version_fingerprint')
