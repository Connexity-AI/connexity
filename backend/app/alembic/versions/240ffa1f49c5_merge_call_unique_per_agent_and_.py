"""merge call_unique_per_agent and deployments heads

Revision ID: 240ffa1f49c5
Revises: d0e1f2a3b4c5, h5i6j7k8l9m0
Create Date: 2026-04-29 13:06:28.828272

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '240ffa1f49c5'
down_revision = ('d0e1f2a3b4c5', 'h5i6j7k8l9m0')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
