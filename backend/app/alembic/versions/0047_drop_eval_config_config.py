"""Drop eval_config.config, which nothing reads or writes

Revision ID: 0047_drop_eval_config_config
Revises: 0046_password_reset
Create Date: 2026-11-23 18:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0047_drop_eval_config_config'
down_revision = '0046_password_reset'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('eval_config', 'config')


def downgrade() -> None:
    op.add_column(
        'eval_config',
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
