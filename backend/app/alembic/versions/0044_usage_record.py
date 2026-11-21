"""Usage per workspace: a record per real call and per simulated call, filled in for
the calls and runs already stored

Revision ID: 0044_usage_record
Revises: 0043_schema_check
Create Date: 2026-11-21 12:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision = '0044_usage_record'
down_revision = '0043_schema_check'
branch_labels = None
depends_on = None


# Usage before this change (Dmytro, 2026-11-21: fill it in). The same counting as
# `app/crud/usage.py`: each started minute of a real call that has ended, and each
# message the simulated caller sent.
BACKFILL_CALLS = """
INSERT INTO usage_record (
    id, company_id, agent_id, meter, quantity, occurred_at, source_key,
    call_id, own_cost_usd, model, input_tokens, output_tokens,
    cache_read_tokens, cache_write_tokens
)
SELECT
    gen_random_uuid(), c.company_id, c.agent_id, 'observed_minutes',
    ceil(extract(epoch FROM (c.ended_at - c.started_at)) / 60.0)::int,
    c.started_at AT TIME ZONE 'UTC', 'call:' || c.id, c.id,
    coalesce(m.cost_usd, 0), coalesce(m.model, ''),
    coalesce(m.input_tokens, 0), coalesce(m.output_tokens, 0), 0, 0
FROM call c
LEFT JOIN (
    SELECT call_id, sum(cost_usd) AS cost_usd, max(model) AS model,
           sum(input_tokens) AS input_tokens,
           sum(output_tokens) AS output_tokens
    FROM model_answer GROUP BY call_id
) m ON m.call_id = c.id
WHERE c.source = 'production'
  AND c.ended_at IS NOT NULL
  AND c.ended_at > c.started_at
ON CONFLICT (source_key) DO NOTHING
"""

BACKFILL_SIMULATED = """
INSERT INTO usage_record (
    id, company_id, agent_id, meter, quantity, occurred_at, source_key,
    test_case_result_id, run_id, own_cost_usd, model, input_tokens,
    output_tokens, cache_read_tokens, cache_write_tokens
)
SELECT
    gen_random_uuid(), t.company_id, r.agent_id, 'simulated_caller_messages',
    t.messages,
    coalesce(t.completed_at, t.created_at) AT TIME ZONE 'UTC',
    'simulated:' || t.id, t.id, t.run_id,
    coalesce(t.platform_cost_usd, 0), '',
    coalesce((t.platform_token_usage ->> 'prompt_tokens')::int, 0),
    coalesce((t.platform_token_usage ->> 'completion_tokens')::int, 0),
    coalesce((t.platform_token_usage ->> 'cache_read_input_tokens')::int, 0),
    coalesce((t.platform_token_usage ->> 'cache_creation_input_tokens')::int, 0)
FROM (
    SELECT tcr.*, (
        SELECT count(*) FROM jsonb_array_elements(
            CASE WHEN jsonb_typeof(tcr.transcript) = 'array'
                 THEN tcr.transcript ELSE '[]'::jsonb END
        ) turn
        WHERE turn ->> 'role' = 'user'
    )::int AS messages
    FROM test_case_result tcr
) t
JOIN run r ON r.id = t.run_id
WHERE t.messages > 0
ON CONFLICT (source_key) DO NOTHING
"""


def upgrade() -> None:
    op.create_table(
        'usage_record',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('agent_id', sa.Uuid(), nullable=False),
        sa.Column('meter', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('call_id', sa.Uuid(), nullable=True),
        sa.Column('test_case_result_id', sa.Uuid(), nullable=True),
        sa.Column('run_id', sa.Uuid(), nullable=True),
        sa.Column('own_cost_usd', sa.Float(), nullable=False),
        sa.Column('model', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('cache_read_tokens', sa.Integer(), nullable=False),
        sa.Column('cache_write_tokens', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent.id']),
        sa.ForeignKeyConstraint(['call_id'], ['call.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['company_id'], ['company.id']),
        sa.ForeignKeyConstraint(['run_id'], ['run.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['test_case_result_id'], ['test_case_result.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_key', name='uq_usage_record_source_key'),
    )
    op.create_index(op.f('ix_usage_record_agent_id'), 'usage_record', ['agent_id'])
    op.create_index(op.f('ix_usage_record_call_id'), 'usage_record', ['call_id'])
    op.create_index(op.f('ix_usage_record_company_id'), 'usage_record', ['company_id'])
    op.create_index('ix_usage_record_company_occurred', 'usage_record', ['company_id', 'occurred_at'])
    op.create_index(op.f('ix_usage_record_run_id'), 'usage_record', ['run_id'])
    op.create_index(op.f('ix_usage_record_test_case_result_id'), 'usage_record', ['test_case_result_id'])
    op.execute(BACKFILL_CALLS)
    op.execute(BACKFILL_SIMULATED)


def downgrade() -> None:
    op.drop_table('usage_record')
