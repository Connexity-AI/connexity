"""agent versioning: agent_version table, agent.version, run agent_version refs

Revision ID: b7c8d9e0f1a2
Revises: f0a1b2c3d4e5
Create Date: 2026-04-07 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "b7c8d9e0f1a2"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_version",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("endpoint_url", sa.String(length=2048), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("tools", JSONB, nullable=True),
        sa.Column("agent_model", sa.String(length=255), nullable=True),
        sa.Column("agent_provider", sa.String(length=64), nullable=True),
        sa.Column("change_description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agent.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "version", name="uq_agent_version_agent_version"),
    )
    op.create_index(op.f("ix_agent_version_agent_id"), "agent_version", ["agent_id"])
    op.create_index(
        "ix_agent_version_agent_id_created_at_desc",
        "agent_version",
        ["agent_id", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        op.f("ix_agent_version_created_by"), "agent_version", ["created_by"]
    )

    op.add_column(
        "agent",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO agent_version (
                id, agent_id, version, mode, endpoint_url, system_prompt,
                tools, agent_model, agent_provider, change_description,
                created_by, created_at
            )
            SELECT gen_random_uuid(), id, 1, mode, endpoint_url, system_prompt,
                   tools, agent_model, agent_provider, NULL, NULL, created_at
            FROM agent
            """
        )
    )

    op.add_column("run", sa.Column("agent_version", sa.Integer(), nullable=True))
    op.add_column("run", sa.Column("agent_version_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_run_agent_version"), "run", ["agent_version"])
    op.create_index(
        op.f("ix_run_agent_version_id"), "run", ["agent_version_id"]
    )
    op.create_foreign_key(
        "fk_run_agent_version_id",
        "run",
        "agent_version",
        ["agent_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_run_agent_version_id", "run", type_="foreignkey")
    op.drop_index(op.f("ix_run_agent_version_id"), table_name="run")
    op.drop_index(op.f("ix_run_agent_version"), table_name="run")
    op.drop_column("run", "agent_version_id")
    op.drop_column("run", "agent_version")

    op.drop_column("agent", "version")

    op.drop_index(op.f("ix_agent_version_created_by"), table_name="agent_version")
    op.drop_index("ix_agent_version_agent_id_created_at_desc", table_name="agent_version")
    op.drop_index(op.f("ix_agent_version_agent_id"), table_name="agent_version")
    op.drop_table("agent_version")
