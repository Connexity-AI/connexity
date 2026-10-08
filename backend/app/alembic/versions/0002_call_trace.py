"""call trace: provider-neutral call columns, event rows, component rows

Revision ID: 0002_call_trace
Revises: 0001_baseline
Create Date: 2026-10-08

The call table stops naming Retell: ``retell_call_id`` becomes ``external_id`` and
``retell_agent_id`` becomes ``provider_agent_id`` (renamed in place, data kept), and a
``provider`` column is filled from each call's integration. Trace events and
components get one row each; there is no stored trace document.
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_call_trace'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('call_component',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('call_id', sa.Uuid(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('ref', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('version', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('fingerprint', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.ForeignKeyConstraint(['call_id'], ['call.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('call_id', 'seq', name='uq_call_component_call_seq')
    )
    op.create_index(op.f('ix_call_component_call_id'), 'call_component', ['call_id'], unique=False)
    op.create_index(op.f('ix_call_component_company_id'), 'call_component', ['company_id'], unique=False)
    op.create_index('ix_call_component_kind_ref_version', 'call_component', ['kind', 'ref', 'version'], unique=False)
    op.create_table('call_event',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('call_id', sa.Uuid(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('type', sa.Enum('utterance', 'tool_call', 'marker', name='calleventtype', native_enum=False, length=32), nullable=False),
    sa.Column('start_ms', sa.Integer(), nullable=True),
    sa.Column('end_ms', sa.Integer(), nullable=True),
    sa.Column('span_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
    sa.Column('speaker', sa.Enum('agent', 'caller', name='speaker', native_enum=False, length=32), nullable=True),
    sa.Column('text', sa.Text(), nullable=True),
    sa.Column('interrupted', sa.Boolean(), nullable=True),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('status', sa.Enum('ok', 'error', 'timeout', 'no_result', name='toolcallstatus', native_enum=False, length=32), nullable=True),
    sa.Column('arguments', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('result', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('detail', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['call_id'], ['call.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('call_id', 'key', name='uq_call_event_call_key'),
    sa.UniqueConstraint('call_id', 'seq', name='uq_call_event_call_seq')
    )
    op.create_index(op.f('ix_call_event_call_id'), 'call_event', ['call_id'], unique=False)
    op.create_index(op.f('ix_call_event_company_id'), 'call_event', ['company_id'], unique=False)
    op.create_index('ix_call_event_type_name', 'call_event', ['type', 'name'], unique=False)
    # Renamed in place so existing calls keep their identifiers.
    op.alter_column('call', 'retell_call_id', new_column_name='external_id')
    op.alter_column('call', 'retell_agent_id', new_column_name='provider_agent_id')

    # Existing calls take their provider from the integration they were synced through.
    op.add_column('call', sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.execute(
        "UPDATE call SET provider = integration.provider "
        "FROM integration WHERE call.integration_id = integration.id"
    )
    op.execute("UPDATE call SET provider = 'unknown' WHERE provider IS NULL")
    op.alter_column('call', 'provider', nullable=False)

    op.add_column('call', sa.Column('schema_version', sa.Integer(), nullable=True))
    op.add_column('call', sa.Column('source', sa.Enum('production', 'test_call', 'simulation', name='tracesource', native_enum=False, length=32), nullable=False, server_default='production'))
    op.alter_column('call', 'source', server_default=None)
    op.add_column('call', sa.Column('channel', sa.Enum('phone', 'web', 'text', name='callchannel', native_enum=False, length=32), nullable=True))
    op.add_column('call', sa.Column('direction', sa.Enum('inbound', 'outbound', name='calldirection', native_enum=False, length=32), nullable=True))
    op.add_column('call', sa.Column('ended_at', sa.DateTime(), nullable=True))
    op.add_column('call', sa.Column('end_reason', sa.Enum('caller_hangup', 'agent_hangup', 'transfer', 'voicemail', 'no_answer', 'error', 'limit', 'unknown', name='callendreason', native_enum=False, length=32), nullable=True))
    op.add_column('call', sa.Column('end_reason_detail', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
    op.add_column('call', sa.Column('trace_id', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('call', sa.Column('agent_number', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('call', sa.Column('caller_number', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('call', sa.Column('recording_url', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True))
    op.add_column('call', sa.Column('reports_tool_calls', sa.Boolean(), nullable=True))
    op.add_column('call', sa.Column('inputs', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True))
    op.add_column('call', sa.Column('outputs', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True))
    op.add_column('call', sa.Column('extensions', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True))
    op.drop_index('ix_call_retell_agent_id', table_name='call')
    op.drop_index('ix_call_retell_call_id', table_name='call')
    op.drop_constraint('uq_call_retell_call_agent', 'call', type_='unique')
    op.create_index(op.f('ix_call_caller_number'), 'call', ['caller_number'], unique=False)
    op.create_index(op.f('ix_call_end_reason'), 'call', ['end_reason'], unique=False)
    op.create_index(op.f('ix_call_external_id'), 'call', ['external_id'], unique=False)
    op.create_index(op.f('ix_call_provider'), 'call', ['provider'], unique=False)
    op.create_index(op.f('ix_call_provider_agent_id'), 'call', ['provider_agent_id'], unique=False)
    op.create_index(op.f('ix_call_source'), 'call', ['source'], unique=False)
    op.create_index(op.f('ix_call_trace_id'), 'call', ['trace_id'], unique=False)
    op.create_unique_constraint('uq_call_external_id_agent', 'call', ['external_id', 'agent_id'])


def downgrade() -> None:
    op.drop_constraint('uq_call_external_id_agent', 'call', type_='unique')
    op.drop_index(op.f('ix_call_trace_id'), table_name='call')
    op.drop_index(op.f('ix_call_source'), table_name='call')
    op.drop_index(op.f('ix_call_provider_agent_id'), table_name='call')
    op.drop_index(op.f('ix_call_provider'), table_name='call')
    op.drop_index(op.f('ix_call_external_id'), table_name='call')
    op.drop_index(op.f('ix_call_end_reason'), table_name='call')
    op.drop_index(op.f('ix_call_caller_number'), table_name='call')
    op.alter_column('call', 'external_id', new_column_name='retell_call_id')
    op.alter_column('call', 'provider_agent_id', new_column_name='retell_agent_id')
    op.create_unique_constraint('uq_call_retell_call_agent', 'call', ['retell_call_id', 'agent_id'])
    op.create_index('ix_call_retell_call_id', 'call', ['retell_call_id'], unique=False)
    op.create_index('ix_call_retell_agent_id', 'call', ['retell_agent_id'], unique=False)
    op.drop_column('call', 'extensions')
    op.drop_column('call', 'outputs')
    op.drop_column('call', 'inputs')
    op.drop_column('call', 'reports_tool_calls')
    op.drop_column('call', 'recording_url')
    op.drop_column('call', 'caller_number')
    op.drop_column('call', 'agent_number')
    op.drop_column('call', 'trace_id')
    op.drop_column('call', 'end_reason_detail')
    op.drop_column('call', 'end_reason')
    op.drop_column('call', 'ended_at')
    op.drop_column('call', 'direction')
    op.drop_column('call', 'channel')
    op.drop_column('call', 'source')
    op.drop_column('call', 'schema_version')
    op.drop_column('call', 'provider')
    op.drop_index('ix_call_event_type_name', table_name='call_event')
    op.drop_index(op.f('ix_call_event_company_id'), table_name='call_event')
    op.drop_index(op.f('ix_call_event_call_id'), table_name='call_event')
    op.drop_table('call_event')
    op.drop_index('ix_call_component_kind_ref_version', table_name='call_component')
    op.drop_index(op.f('ix_call_component_company_id'), table_name='call_component')
    op.drop_index(op.f('ix_call_component_call_id'), table_name='call_component')
    op.drop_table('call_component')
