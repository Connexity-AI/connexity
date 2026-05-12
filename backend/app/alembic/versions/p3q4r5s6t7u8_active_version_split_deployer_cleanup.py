"""active agent_version flag, split version labels, drop agent.version and deployed_by_name

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2026-05-07

"""

import sqlalchemy as sa
from alembic import op

revision = "p3q4r5s6t7u8"
down_revision = "o2p3q4r5s6t7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_version",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "agent_version",
        sa.Column("version_name", sa.Text(), nullable=True),
    )
    op.add_column(
        "agent_version",
        sa.Column("version_description", sa.Text(), nullable=True),
    )

    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            UPDATE agent_version
            SET
              version_name = CASE
                WHEN change_description IS NULL OR trim(change_description) = '' THEN NULL
                ELSE trim(split_part(change_description, E'\\n', 1))
              END,
              version_description = CASE
                WHEN change_description IS NULL OR strpos(change_description, E'\\n') = 0 THEN NULL
                ELSE trim(substring(change_description from strpos(change_description, E'\\n') + 1))
              END
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE agent_version av
            SET is_active = true
            FROM agent a
            WHERE av.agent_id = a.id
              AND av.version = a.version
              AND av.status = 'published'
              AND a.version IS NOT NULL
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE agent_version av
            SET is_active = true
            FROM (
              SELECT DISTINCT ON (agent_id) id
              FROM agent_version
              WHERE status = 'published' AND version IS NOT NULL
              ORDER BY agent_id, version DESC
            ) latest
            WHERE av.id = latest.id
              AND NOT EXISTS (
                SELECT 1
                FROM agent_version z
                WHERE z.agent_id = av.agent_id AND z.is_active
              )
            """
        )
    )

    op.drop_column("agent_version", "change_description")

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

    op.drop_column("deployment", "deployed_by_name")
    op.drop_column("agent", "version")


def downgrade() -> None:
    op.add_column(
        "agent",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )

    op.add_column(
        "deployment",
        sa.Column("deployed_by_name", sa.String(length=255), nullable=True),
    )

    op.drop_index(
        "ix_agent_version_one_active_published_per_agent",
        table_name="agent_version",
    )
    op.drop_constraint("ck_agent_version_active_rules", "agent_version", type_="check")

    op.add_column(
        "agent_version",
        sa.Column("change_description", sa.Text(), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE agent_version
            SET change_description = CASE
              WHEN version_name IS NULL AND version_description IS NULL THEN NULL
              WHEN version_description IS NULL OR trim(version_description) = '' THEN version_name
              WHEN version_name IS NULL OR trim(version_name) = '' THEN version_description
              ELSE version_name || E'\\n' || version_description
            END
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE agent a
            SET version = COALESCE(
              (
                SELECT av.version
                FROM agent_version av
                WHERE av.agent_id = a.id AND av.is_active AND av.status = 'published'
                LIMIT 1
              ),
              (
                SELECT MAX(av.version)
                FROM agent_version av
                WHERE av.agent_id = a.id AND av.status = 'published' AND av.version IS NOT NULL
              ),
              1
            )
            """
        )
    )

    op.drop_column("agent_version", "is_active")
    op.drop_column("agent_version", "version_name")
    op.drop_column("agent_version", "version_description")

    op.alter_column(
        "agent",
        "version",
        server_default=None,
    )
