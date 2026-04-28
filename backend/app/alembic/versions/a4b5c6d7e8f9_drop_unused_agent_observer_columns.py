"""drop unused agent observer columns

Revision ID: a4b5c6d7e8f9
Revises: 5fac2991a010
Create Date: 2026-04-27 00:00:00.000000

The agent.integration_id and agent.retell_agent_id columns were added in
5fac2991a010 but never read — call ingestion goes through Environment instead.
Drop them so the schema reflects actual usage.
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'a4b5c6d7e8f9'
down_revision = '5fac2991a010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('fk_agent_integration_id', 'agent', type_='foreignkey')
    op.drop_index(op.f('ix_agent_retell_agent_id'), table_name='agent')
    op.drop_index(op.f('ix_agent_integration_id'), table_name='agent')
    op.drop_column('agent', 'retell_agent_id')
    op.drop_column('agent', 'integration_id')


def downgrade() -> None:
    op.add_column(
        'agent',
        sa.Column(
            'retell_agent_id',
            sqlmodel.sql.sqltypes.AutoString(length=255),
            nullable=True,
        ),
    )
    op.add_column('agent', sa.Column('integration_id', sa.Uuid(), nullable=True))
    op.create_index(
        op.f('ix_agent_integration_id'), 'agent', ['integration_id'], unique=False
    )
    op.create_index(
        op.f('ix_agent_retell_agent_id'), 'agent', ['retell_agent_id'], unique=False
    )
    op.create_foreign_key(
        'fk_agent_integration_id',
        'agent',
        'integration',
        ['integration_id'],
        ['id'],
    )
