"""n8n: connection address, tool-to-workflow mapping, executions and their steps

Revision ID: 0005_n8n_executions
Revises: 0004_call_drop_provider_columns
Create Date: 2026-10-09
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005_n8n_executions'
down_revision = '0004_call_drop_provider_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('agent_tool_backend',
    sa.Column('agent_id', sa.Uuid(), nullable=False),
    sa.Column('tool_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('integration_id', sa.Uuid(), nullable=False),
    sa.Column('workflow_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('workflow_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['integration_id'], ['integration.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('agent_id', 'tool_name')
    )
    op.create_index(op.f('ix_agent_tool_backend_company_id'), 'agent_tool_backend', ['company_id'], unique=False)
    op.create_index(op.f('ix_agent_tool_backend_integration_id'), 'agent_tool_backend', ['integration_id'], unique=False)
    op.create_table('call_execution',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('call_id', sa.Uuid(), nullable=False),
    sa.Column('event_key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('integration_id', sa.Uuid(), nullable=True),
    sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('external_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('workflow_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
    sa.Column('workflow_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('workflow_version', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('status', sa.Enum('ok', 'error', 'running', 'canceled', 'unknown', name='executionstatus', native_enum=False, length=32), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('ended_at', sa.DateTime(), nullable=True),
    sa.Column('match', sa.Enum('exact', 'guess', name='executionmatch', native_enum=False, length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['call_id'], ['call.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['integration_id'], ['integration.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('call_id', 'event_key', name='uq_call_execution_call_event')
    )
    op.create_index(op.f('ix_call_execution_call_id'), 'call_execution', ['call_id'], unique=False)
    op.create_index(op.f('ix_call_execution_company_id'), 'call_execution', ['company_id'], unique=False)
    op.create_index(op.f('ix_call_execution_integration_id'), 'call_execution', ['integration_id'], unique=False)
    op.create_table('call_execution_step',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('execution_id', sa.Uuid(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('status', sa.Enum('ok', 'error', 'running', 'canceled', 'unknown', name='executionstatus', native_enum=False, length=32), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('input_from', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('output', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('error', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('data_dropped', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['execution_id'], ['call_execution.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('execution_id', 'seq', name='uq_call_execution_step_seq')
    )
    op.create_index(op.f('ix_call_execution_step_company_id'), 'call_execution_step', ['company_id'], unique=False)
    op.create_index(op.f('ix_call_execution_step_execution_id'), 'call_execution_step', ['execution_id'], unique=False)
    op.add_column('integration', sa.Column('base_url', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column('integration', 'base_url')
    op.drop_index(op.f('ix_call_execution_step_execution_id'), table_name='call_execution_step')
    op.drop_index(op.f('ix_call_execution_step_company_id'), table_name='call_execution_step')
    op.drop_table('call_execution_step')
    op.drop_index(op.f('ix_call_execution_integration_id'), table_name='call_execution')
    op.drop_index(op.f('ix_call_execution_company_id'), table_name='call_execution')
    op.drop_index(op.f('ix_call_execution_call_id'), table_name='call_execution')
    op.drop_table('call_execution')
    op.drop_index(op.f('ix_agent_tool_backend_integration_id'), table_name='agent_tool_backend')
    op.drop_index(op.f('ix_agent_tool_backend_company_id'), table_name='agent_tool_backend')
    op.drop_table('agent_tool_backend')
