"""merge deployments and platform_tools_mode heads

Revision ID: af913b8f8d16
Revises: 240ffa1f49c5, e8f9a0b1c2d3
Create Date: 2026-04-30 08:52:40.787667

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'af913b8f8d16'
down_revision = ('240ffa1f49c5', 'e8f9a0b1c2d3')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
