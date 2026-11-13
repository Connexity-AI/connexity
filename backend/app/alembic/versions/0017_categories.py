"""categories: one fixed, Connexity-wide set; every issue belongs to one

Revision ID: 0017_categories
Revises: 0016_scheduled_call_pull
Create Date: 2026-11-13 15:45:00.000000

"""
import uuid

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0017_categories'
down_revision = '0016_scheduled_call_pull'
branch_labels = None
depends_on = None

# Design prompt 06, in order. Copied here so the migration never changes with the code.
SEED = [
    ("greeting_and_identification", "Greeting and identification", "behaviour"),
    ("information_collection", "Information collection", "behaviour"),
    ("booking", "Booking", "behaviour"),
    ("rescheduling_and_cancelling", "Rescheduling and cancelling", "behaviour"),
    ("pricing_and_quotes", "Pricing and quotes", "behaviour"),
    ("objection_handling", "Objection handling", "behaviour"),
    ("transfers_and_escalation", "Transfers and escalation", "behaviour"),
    ("compliance_and_privacy", "Compliance and privacy", "behaviour"),
    ("conversation_flow_quality", "Conversation flow quality", "behaviour"),
    ("ending_the_call", "Ending the call", "behaviour"),
    ("responsiveness", "Responsiveness", "technical"),
    ("tools_and_integrations", "Tools and integrations", "technical"),
    ("speech_recognition", "Speech recognition", "technical"),
    ("other", "Other", "behaviour"),
]
# The category each check type already in use belongs to; any other gets "other".
CHECK_CATEGORIES = {"tool_call_failed": "tools_and_integrations"}


def upgrade() -> None:
    category = op.create_table('category',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('behaviour', 'technical', name='categorykind', native_enum=False, length=32), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.bulk_insert(category, [
        {"id": uuid.uuid4(), "key": key, "name": name, "position": i, "kind": kind}
        for i, (key, name, kind) in enumerate(SEED, start=1)
    ])

    op.add_column('issue', sa.Column('category_id', sa.Uuid(), nullable=True))
    for check_type, key in CHECK_CATEGORIES.items():
        op.execute(sa.text(
            "UPDATE issue SET category_id = (SELECT id FROM category WHERE key = :key) "
            "WHERE check_type = :check_type"
        ).bindparams(key=key, check_type=check_type))
    op.execute("UPDATE issue SET category_id = (SELECT id FROM category WHERE key = 'other') WHERE category_id IS NULL")
    op.alter_column('issue', 'category_id', nullable=False)
    op.create_index(op.f('ix_issue_category_id'), 'issue', ['category_id'], unique=False)
    op.create_foreign_key('issue_category_id_fkey', 'issue', 'category', ['category_id'], ['id'], ondelete='RESTRICT')


def downgrade() -> None:
    op.drop_constraint('issue_category_id_fkey', 'issue', type_='foreignkey')
    op.drop_index(op.f('ix_issue_category_id'), table_name='issue')
    op.drop_column('issue', 'category_id')
    op.drop_table('category')
