"""merge integrations and eval_config heads

Revision ID: 0b1519d085ff
Revises: cfaa27c727d5, 3fd6a2a5fda5
Create Date: 2026-04-21 15:29:10.116695

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0b1519d085ff'
down_revision = ('cfaa27c727d5', '3fd6a2a5fda5')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
