"""baseline: the full Connexity schema as of the 2.0 rebuild

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-06

Replaces the 64 revisions of Connexity 1.x. Generated from the models, so the
models are the single description of the schema. A database created by the
old revisions cannot be upgraded to this one: recreate it.

Conventions fixed here:
- every enum column is a VARCHAR holding the member's value (no Postgres ENUM
  types), see ``app.models.columns.enum_type``
- defaults live in the models, not in server defaults, except timestamps
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('company',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('openai_api_key_encrypted', sa.Text(), nullable=True),
    sa.Column('openai_api_key_masked', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=True),
    sa.Column('anthropic_api_key_encrypted', sa.Text(), nullable=True),
    sa.Column('anthropic_api_key_masked', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=True),
    sa.Column('preferred_llm_provider', sa.Enum('openai', 'anthropic', name='llmprovider', native_enum=False, length=32), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('oauth_client',
    sa.Column('client_id', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
    sa.Column('client_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('redirect_uris', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('grant_types', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('response_types', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('scope', sa.Text(), nullable=True),
    sa.Column('token_endpoint_auth_method', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('raw_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('client_id')
    )
    op.create_table('integration',
    sa.Column('provider', sa.Enum('retell', 'vapi', 'elevenlabs', name='integrationprovider', native_enum=False, length=32), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('encrypted_api_key', sa.Text(), nullable=False),
    sa.Column('masked_api_key', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_company_id'), 'integration', ['company_id'], unique=False)
    op.create_index(op.f('ix_integration_provider'), 'integration', ['provider'], unique=False)
    op.create_table('user',
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('provider', sa.Enum('email', 'github', name='authprovider', native_enum=False, length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('full_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('hashed_password', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_company_id'), 'user', ['company_id'], unique=False)
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_table('agent',
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('mode', sa.Enum('endpoint', 'platform', name='agentmode', native_enum=False, length=32), nullable=False),
    sa.Column('platform', sa.Enum('retell', 'vapi', 'elevenlabs', 'webhook', name='platform', native_enum=False, length=32), nullable=True),
    sa.Column('prompt_type', sa.Enum('single_prompt', 'multi_prompt', name='agentprompttype', native_enum=False, length=32), nullable=False),
    sa.Column('integration_id', sa.Uuid(), nullable=True),
    sa.Column('platform_agent_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('platform_agent_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('endpoint_url', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
    sa.Column('system_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('tools', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('agent_model', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('agent_provider', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
    sa.Column('agent_temperature', sa.Float(), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('has_draft', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('calls_last_synced_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
    sa.ForeignKeyConstraint(['integration_id'], ['integration.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_company_id'), 'agent', ['company_id'], unique=False)
    op.create_index(op.f('ix_agent_created_by'), 'agent', ['created_by'], unique=False)
    op.create_index(op.f('ix_agent_integration_id'), 'agent', ['integration_id'], unique=False)
    op.create_table('custom_metric',
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('display_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('tier', sa.Enum('execution', 'knowledge', 'process', 'delivery', name='metrictier', native_enum=False, length=32), nullable=False),
    sa.Column('default_weight', sa.Float(), nullable=False),
    sa.Column('score_type', sa.Enum('scored', 'binary', name='scoretype', native_enum=False, length=32), nullable=False),
    sa.Column('rubric', sa.Text(), nullable=False),
    sa.Column('include_in_defaults', sa.Boolean(), nullable=False),
    sa.Column('is_predefined', sa.Boolean(), nullable=False),
    sa.Column('is_draft', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_custom_metric_company_id'), 'custom_metric', ['company_id'], unique=False)
    op.create_index(op.f('ix_custom_metric_created_by'), 'custom_metric', ['created_by'], unique=False)
    op.create_index(op.f('ix_custom_metric_deleted_at'), 'custom_metric', ['deleted_at'], unique=False)
    op.create_index('uq_custom_metric_company_name_active', 'custom_metric', ['company_id', 'name'], unique=True, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_table('oauth_authorization_code',
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('client_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('redirect_uri', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=False),
    sa.Column('scope', sa.Text(), nullable=True),
    sa.Column('resource', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=False),
    sa.Column('code_challenge', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('code_challenge_method', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('consumed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['oauth_client.client_id'], ),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('code')
    )
    op.create_index(op.f('ix_oauth_authorization_code_client_id'), 'oauth_authorization_code', ['client_id'], unique=False)
    op.create_index(op.f('ix_oauth_authorization_code_company_id'), 'oauth_authorization_code', ['company_id'], unique=False)
    op.create_index(op.f('ix_oauth_authorization_code_user_id'), 'oauth_authorization_code', ['user_id'], unique=False)
    op.create_table('oauth_refresh_token',
    sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('client_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('scope', sa.Text(), nullable=True),
    sa.Column('resource', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['oauth_client.client_id'], ),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('token_hash')
    )
    op.create_index(op.f('ix_oauth_refresh_token_client_id'), 'oauth_refresh_token', ['client_id'], unique=False)
    op.create_index(op.f('ix_oauth_refresh_token_company_id'), 'oauth_refresh_token', ['company_id'], unique=False)
    op.create_index(op.f('ix_oauth_refresh_token_user_id'), 'oauth_refresh_token', ['user_id'], unique=False)
    op.create_table('agent_version',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('agent_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('draft', 'published', name='agentversionstatus', native_enum=False, length=32), nullable=False),
    sa.Column('mode', sa.Enum('endpoint', 'platform', name='agentmode', native_enum=False, length=32), nullable=False),
    sa.Column('endpoint_url', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
    sa.Column('system_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('tools', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('agent_model', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('agent_provider', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
    sa.Column('agent_temperature', sa.Float(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('version_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('version_description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('NOT is_active OR version IS NOT NULL', name='ck_agent_version_active_rules'),
    sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('agent_id', 'version', name='uq_agent_version_agent_version')
    )
    op.create_index(op.f('ix_agent_version_agent_id'), 'agent_version', ['agent_id'], unique=False)
    op.create_index('ix_agent_version_agent_id_created_at_desc', 'agent_version', ['agent_id', sa.text('created_at DESC')], unique=False)
    op.create_index(op.f('ix_agent_version_company_id'), 'agent_version', ['company_id'], unique=False)
    op.create_index(op.f('ix_agent_version_created_by'), 'agent_version', ['created_by'], unique=False)
    op.create_index('ix_agent_version_one_active_published_per_agent', 'agent_version', ['agent_id'], unique=True, postgresql_where=sa.text('is_active AND version IS NOT NULL'))
    op.create_index('ix_agent_version_one_draft_per_agent', 'agent_version', ['agent_id'], unique=True, postgresql_where=sa.text("status = 'draft'"))
    op.create_table('call',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('agent_id', sa.Uuid(), nullable=False),
    sa.Column('integration_id', sa.Uuid(), nullable=True),
    sa.Column('retell_call_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('retell_agent_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('duration_seconds', sa.Integer(), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
    sa.Column('transcript', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('seen_at', sa.DateTime(), nullable=True),
    sa.Column('label', sa.Enum('good', 'bad', name='calllabel', native_enum=False, length=32), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['integration_id'], ['integration.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('retell_call_id', 'agent_id', name='uq_call_retell_call_agent')
    )
    op.create_index(op.f('ix_call_agent_id'), 'call', ['agent_id'], unique=False)
    op.create_index(op.f('ix_call_company_id'), 'call', ['company_id'], unique=False)
    op.create_index(op.f('ix_call_deleted_at'), 'call', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_call_integration_id'), 'call', ['integration_id'], unique=False)
    op.create_index(op.f('ix_call_retell_agent_id'), 'call', ['retell_agent_id'], unique=False)
    op.create_index(op.f('ix_call_retell_call_id'), 'call', ['retell_call_id'], unique=False)
    op.create_index(op.f('ix_call_started_at'), 'call', ['started_at'], unique=False)
    op.create_table('environment',
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('platform', sa.Enum('retell', 'vapi', 'elevenlabs', 'webhook', name='platform', native_enum=False, length=32), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('agent_id', sa.Uuid(), nullable=False),
    sa.Column('endpoint_url', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_environment_agent_id'), 'environment', ['agent_id'], unique=False)
    op.create_index(op.f('ix_environment_company_id'), 'environment', ['company_id'], unique=False)
    op.create_table('eval_config',
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('agent_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_eval_config_agent_id'), 'eval_config', ['agent_id'], unique=False)
    op.create_index(op.f('ix_eval_config_company_id'), 'eval_config', ['company_id'], unique=False)
    op.create_index(op.f('ix_eval_config_deleted_at'), 'eval_config', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_eval_config_name'), 'eval_config', ['name'], unique=False)
    op.create_table('run',
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('agent_id', sa.Uuid(), nullable=False),
    sa.Column('agent_endpoint_url', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
    sa.Column('agent_system_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('agent_tools', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('agent_mode', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
    sa.Column('agent_model', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('agent_provider', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
    sa.Column('eval_config_id', sa.Uuid(), nullable=False),
    sa.Column('eval_config_version', sa.Integer(), nullable=False),
    sa.Column('agent_version', sa.Integer(), nullable=True),
    sa.Column('agent_version_id', sa.Uuid(), nullable=True),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', 'cancelled', name='runstatus', native_enum=False, length=32), nullable=False),
    sa.Column('is_baseline', sa.Boolean(), nullable=False),
    sa.Column('aggregate_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ),
    sa.ForeignKeyConstraint(['agent_version_id'], ['agent_version.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
    sa.ForeignKeyConstraint(['eval_config_id'], ['eval_config.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_run_agent_id'), 'run', ['agent_id'], unique=False)
    op.create_index(op.f('ix_run_agent_version'), 'run', ['agent_version'], unique=False)
    op.create_index(op.f('ix_run_agent_version_id'), 'run', ['agent_version_id'], unique=False)
    op.create_index(op.f('ix_run_company_id'), 'run', ['company_id'], unique=False)
    op.create_index(op.f('ix_run_created_at'), 'run', ['created_at'], unique=False)
    op.create_index(op.f('ix_run_created_by'), 'run', ['created_by'], unique=False)
    op.create_index(op.f('ix_run_eval_config_id'), 'run', ['eval_config_id'], unique=False)
    op.create_index(op.f('ix_run_is_baseline'), 'run', ['is_baseline'], unique=False)
    op.create_index(op.f('ix_run_status'), 'run', ['status'], unique=False)
    op.create_table('test_case',
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('difficulty', sa.Enum('normal', 'hard', name='difficulty', native_enum=False, length=32), nullable=False),
    sa.Column('tags', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('status', sa.Enum('draft', 'active', 'archived', name='testcasestatus', native_enum=False, length=32), nullable=False),
    sa.Column('persona_context', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('first_turn', sa.Enum('agent', 'user', name='firstturn', native_enum=False, length=32), nullable=False),
    sa.Column('first_message', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('user_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('expected_outcomes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('expected_tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('evaluation_criteria_override', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('agent_id', sa.Uuid(), nullable=True),
    sa.Column('source_call_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['source_call_id'], ['call.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_case_agent_id'), 'test_case', ['agent_id'], unique=False)
    op.create_index(op.f('ix_test_case_company_id'), 'test_case', ['company_id'], unique=False)
    op.create_index(op.f('ix_test_case_deleted_at'), 'test_case', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_test_case_difficulty'), 'test_case', ['difficulty'], unique=False)
    op.create_index(op.f('ix_test_case_source_call_id'), 'test_case', ['source_call_id'], unique=False)
    op.create_index(op.f('ix_test_case_status'), 'test_case', ['status'], unique=False)
    op.create_index('ix_test_case_tags_gin', 'test_case', ['tags'], unique=False, postgresql_using='gin')
    op.create_table('eval_config_member',
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('eval_config_id', sa.Uuid(), nullable=False),
    sa.Column('test_case_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('repetitions', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['eval_config_id'], ['eval_config.id'], ),
    sa.ForeignKeyConstraint(['test_case_id'], ['test_case.id'], ),
    sa.PrimaryKeyConstraint('eval_config_id', 'test_case_id')
    )
    op.create_index(op.f('ix_eval_config_member_company_id'), 'eval_config_member', ['company_id'], unique=False)
    op.create_index(op.f('ix_eval_config_member_eval_config_id'), 'eval_config_member', ['eval_config_id'], unique=False)
    op.create_table('test_case_result',
    sa.Column('run_id', sa.Uuid(), nullable=False),
    sa.Column('test_case_id', sa.Uuid(), nullable=False),
    sa.Column('repetition_index', sa.Integer(), nullable=False),
    sa.Column('transcript', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('turn_count', sa.Integer(), nullable=True),
    sa.Column('verdict', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('total_latency_ms', sa.Integer(), nullable=True),
    sa.Column('agent_latency_p50_ms', sa.Integer(), nullable=True),
    sa.Column('agent_latency_p95_ms', sa.Integer(), nullable=True),
    sa.Column('agent_latency_max_ms', sa.Integer(), nullable=True),
    sa.Column('agent_latency_per_turn_ms', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('agent_token_usage', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('platform_token_usage', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('agent_cost_usd', sa.Float(), nullable=True),
    sa.Column('platform_cost_usd', sa.Float(), nullable=True),
    sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
    sa.Column('passed', sa.Boolean(), nullable=True),
    sa.Column('error_message', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.ForeignKeyConstraint(['test_case_id'], ['test_case.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_case_result_company_id'), 'test_case_result', ['company_id'], unique=False)
    op.create_index(op.f('ix_test_case_result_passed'), 'test_case_result', ['passed'], unique=False)
    op.create_index(op.f('ix_test_case_result_run_id'), 'test_case_result', ['run_id'], unique=False)
    op.create_index(op.f('ix_test_case_result_test_case_id'), 'test_case_result', ['test_case_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_test_case_result_test_case_id'), table_name='test_case_result')
    op.drop_index(op.f('ix_test_case_result_run_id'), table_name='test_case_result')
    op.drop_index(op.f('ix_test_case_result_passed'), table_name='test_case_result')
    op.drop_index(op.f('ix_test_case_result_company_id'), table_name='test_case_result')
    op.drop_table('test_case_result')
    op.drop_index(op.f('ix_eval_config_member_eval_config_id'), table_name='eval_config_member')
    op.drop_index(op.f('ix_eval_config_member_company_id'), table_name='eval_config_member')
    op.drop_table('eval_config_member')
    op.drop_index('ix_test_case_tags_gin', table_name='test_case', postgresql_using='gin')
    op.drop_index(op.f('ix_test_case_status'), table_name='test_case')
    op.drop_index(op.f('ix_test_case_source_call_id'), table_name='test_case')
    op.drop_index(op.f('ix_test_case_difficulty'), table_name='test_case')
    op.drop_index(op.f('ix_test_case_deleted_at'), table_name='test_case')
    op.drop_index(op.f('ix_test_case_company_id'), table_name='test_case')
    op.drop_index(op.f('ix_test_case_agent_id'), table_name='test_case')
    op.drop_table('test_case')
    op.drop_index(op.f('ix_run_status'), table_name='run')
    op.drop_index(op.f('ix_run_is_baseline'), table_name='run')
    op.drop_index(op.f('ix_run_eval_config_id'), table_name='run')
    op.drop_index(op.f('ix_run_created_by'), table_name='run')
    op.drop_index(op.f('ix_run_created_at'), table_name='run')
    op.drop_index(op.f('ix_run_company_id'), table_name='run')
    op.drop_index(op.f('ix_run_agent_version_id'), table_name='run')
    op.drop_index(op.f('ix_run_agent_version'), table_name='run')
    op.drop_index(op.f('ix_run_agent_id'), table_name='run')
    op.drop_table('run')
    op.drop_index(op.f('ix_eval_config_name'), table_name='eval_config')
    op.drop_index(op.f('ix_eval_config_deleted_at'), table_name='eval_config')
    op.drop_index(op.f('ix_eval_config_company_id'), table_name='eval_config')
    op.drop_index(op.f('ix_eval_config_agent_id'), table_name='eval_config')
    op.drop_table('eval_config')
    op.drop_index(op.f('ix_environment_company_id'), table_name='environment')
    op.drop_index(op.f('ix_environment_agent_id'), table_name='environment')
    op.drop_table('environment')
    op.drop_index(op.f('ix_call_started_at'), table_name='call')
    op.drop_index(op.f('ix_call_retell_call_id'), table_name='call')
    op.drop_index(op.f('ix_call_retell_agent_id'), table_name='call')
    op.drop_index(op.f('ix_call_integration_id'), table_name='call')
    op.drop_index(op.f('ix_call_deleted_at'), table_name='call')
    op.drop_index(op.f('ix_call_company_id'), table_name='call')
    op.drop_index(op.f('ix_call_agent_id'), table_name='call')
    op.drop_table('call')
    op.drop_index('ix_agent_version_one_draft_per_agent', table_name='agent_version', postgresql_where=sa.text("status = 'draft'"))
    op.drop_index('ix_agent_version_one_active_published_per_agent', table_name='agent_version', postgresql_where=sa.text('is_active AND version IS NOT NULL'))
    op.drop_index(op.f('ix_agent_version_created_by'), table_name='agent_version')
    op.drop_index(op.f('ix_agent_version_company_id'), table_name='agent_version')
    op.drop_index('ix_agent_version_agent_id_created_at_desc', table_name='agent_version')
    op.drop_index(op.f('ix_agent_version_agent_id'), table_name='agent_version')
    op.drop_table('agent_version')
    op.drop_index(op.f('ix_oauth_refresh_token_user_id'), table_name='oauth_refresh_token')
    op.drop_index(op.f('ix_oauth_refresh_token_company_id'), table_name='oauth_refresh_token')
    op.drop_index(op.f('ix_oauth_refresh_token_client_id'), table_name='oauth_refresh_token')
    op.drop_table('oauth_refresh_token')
    op.drop_index(op.f('ix_oauth_authorization_code_user_id'), table_name='oauth_authorization_code')
    op.drop_index(op.f('ix_oauth_authorization_code_company_id'), table_name='oauth_authorization_code')
    op.drop_index(op.f('ix_oauth_authorization_code_client_id'), table_name='oauth_authorization_code')
    op.drop_table('oauth_authorization_code')
    op.drop_index('uq_custom_metric_company_name_active', table_name='custom_metric', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index(op.f('ix_custom_metric_deleted_at'), table_name='custom_metric')
    op.drop_index(op.f('ix_custom_metric_created_by'), table_name='custom_metric')
    op.drop_index(op.f('ix_custom_metric_company_id'), table_name='custom_metric')
    op.drop_table('custom_metric')
    op.drop_index(op.f('ix_agent_integration_id'), table_name='agent')
    op.drop_index(op.f('ix_agent_created_by'), table_name='agent')
    op.drop_index(op.f('ix_agent_company_id'), table_name='agent')
    op.drop_table('agent')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_index(op.f('ix_user_company_id'), table_name='user')
    op.drop_table('user')
    op.drop_index(op.f('ix_integration_provider'), table_name='integration')
    op.drop_index(op.f('ix_integration_company_id'), table_name='integration')
    op.drop_table('integration')
    op.drop_table('oauth_client')
    op.drop_table('company')
