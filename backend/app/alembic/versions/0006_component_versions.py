"""component versions: the catalogue of versions seen, and each call's state

Revision ID: 0006_component_versions
Revises: 0005_n8n_executions
Create Date: 2026-10-09
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0006_component_versions'
down_revision = '0005_n8n_executions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('component_version',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('company_id', sa.Uuid(), nullable=False),
    sa.Column('agent_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('ref', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('version', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('fingerprint', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('content', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('links', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('first_seen_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('agent_id', 'kind', 'ref', 'version', name='uq_component_version_identity')
    )
    op.create_index(op.f('ix_component_version_agent_id'), 'component_version', ['agent_id'], unique=False)
    op.create_index(op.f('ix_component_version_company_id'), 'component_version', ['company_id'], unique=False)
    op.create_index(op.f('ix_component_version_fingerprint'), 'component_version', ['fingerprint'], unique=False)
    op.add_column('call', sa.Column('agent_version', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
    op.add_column('call', sa.Column('state_fingerprint', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    # Calls already stored know their agent's version; copy it to the new column.
    op.execute(
        """
        UPDATE call SET agent_version = component.version
        FROM (
            SELECT DISTINCT ON (call_id) call_id, version
            FROM call_component
            WHERE kind = 'agent' AND version IS NOT NULL
            ORDER BY call_id, seq
        ) AS component
        WHERE component.call_id = call.id
        """
    )
    op.create_index(op.f('ix_call_state_fingerprint'), 'call', ['state_fingerprint'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_call_state_fingerprint'), table_name='call')
    op.drop_column('call', 'state_fingerprint')
    op.drop_column('call', 'agent_version')
    op.drop_index(op.f('ix_component_version_fingerprint'), table_name='component_version')
    op.drop_index(op.f('ix_component_version_company_id'), table_name='component_version')
    op.drop_index(op.f('ix_component_version_agent_id'), table_name='component_version')
    op.drop_table('component_version')
