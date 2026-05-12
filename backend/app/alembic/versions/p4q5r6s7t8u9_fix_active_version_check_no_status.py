"""fix active version check: use version nullability only (no status string)

Revision ID: p4q5r6s7t8u9
Revises: p3q4r5s6t7u8
Create Date: 2026-05-07

"""

import sqlalchemy as sa
from alembic import op

revision = "p4q5r6s7t8u9"
down_revision = "p3q4r5s6t7u8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "ix_agent_version_one_active_published_per_agent",
        table_name="agent_version",
    )
    op.drop_constraint(
        "ck_agent_version_active_rules",
        "agent_version",
        type_="check",
    )
    op.create_check_constraint(
        "ck_agent_version_active_rules",
        "agent_version",
        "NOT is_active OR version IS NOT NULL",
    )
    op.create_index(
        "ix_agent_version_one_active_published_per_agent",
        "agent_version",
        ["agent_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND version IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_version_one_active_published_per_agent",
        table_name="agent_version",
    )
    op.drop_constraint(
        "ck_agent_version_active_rules",
        "agent_version",
        type_="check",
    )
    op.create_check_constraint(
        "ck_agent_version_active_rules",
        "agent_version",
        "NOT is_active OR (lower(status::text) = 'published' AND version IS NOT NULL)",
    )
    op.create_index(
        "ix_agent_version_one_active_published_per_agent",
        "agent_version",
        ["agent_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND lower(status::text) = 'published'"),
    )
