"""add call observer tables

Revision ID: 5fac2991a010
Revises: e2f3a4b5c6d7
Create Date: 2026-04-23 18:57:21.918535

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5fac2991a010'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Call table
    op.create_table(
        'call',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('agent_id', sa.Uuid(), nullable=False),
        sa.Column('integration_id', sa.Uuid(), nullable=False),
        sa.Column('retell_call_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('retell_agent_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column('transcript', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('seen_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent.id']),
        sa.ForeignKeyConstraint(['integration_id'], ['integration.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_call_agent_id'), 'call', ['agent_id'], unique=False)
    op.create_index(op.f('ix_call_integration_id'), 'call', ['integration_id'], unique=False)
    op.create_index(op.f('ix_call_retell_agent_id'), 'call', ['retell_agent_id'], unique=False)
    op.create_index(op.f('ix_call_retell_call_id'), 'call', ['retell_call_id'], unique=True)
    op.create_index(op.f('ix_call_started_at'), 'call', ['started_at'], unique=False)

    # Agent: retell wiring
    op.add_column('agent', sa.Column('integration_id', sa.Uuid(), nullable=True))
    op.add_column(
        'agent',
        sa.Column('retell_agent_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    )
    op.create_index(op.f('ix_agent_integration_id'), 'agent', ['integration_id'], unique=False)
    op.create_index(op.f('ix_agent_retell_agent_id'), 'agent', ['retell_agent_id'], unique=False)
    op.create_foreign_key(
        'fk_agent_integration_id',
        'agent',
        'integration',
        ['integration_id'],
        ['id'],
    )

    # TestCase: source call link
    op.add_column('test_case', sa.Column('source_call_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_test_case_source_call_id'), 'test_case', ['source_call_id'], unique=False)
    op.create_foreign_key(
        'fk_test_case_source_call_id',
        'test_case',
        'call',
        ['source_call_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_test_case_source_call_id', 'test_case', type_='foreignkey')
    op.drop_index(op.f('ix_test_case_source_call_id'), table_name='test_case')
    op.drop_column('test_case', 'source_call_id')

    op.drop_constraint('fk_agent_integration_id', 'agent', type_='foreignkey')
    op.drop_index(op.f('ix_agent_retell_agent_id'), table_name='agent')
    op.drop_index(op.f('ix_agent_integration_id'), table_name='agent')
    op.drop_column('agent', 'retell_agent_id')
    op.drop_column('agent', 'integration_id')

    op.drop_index(op.f('ix_call_started_at'), table_name='call')
    op.drop_index(op.f('ix_call_retell_call_id'), table_name='call')
    op.drop_index(op.f('ix_call_retell_agent_id'), table_name='call')
    op.drop_index(op.f('ix_call_integration_id'), table_name='call')
    op.drop_index(op.f('ix_call_agent_id'), table_name='call')
    op.drop_table('call')
